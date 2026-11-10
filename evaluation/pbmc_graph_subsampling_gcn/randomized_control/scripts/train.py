#!/usr/bin/env python
"""Randomized control using the unchanged original GLUE runner and GCN audits."""
import argparse
import functools
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import time

from common import (EXPERIMENT,ORIGINAL,INPUT,SHARED,info,save_json,sha,
                    validate_manifest,verify_freeze,use_original,verify_model)


def runner_arguments(row,output,input_dir,smoke):
    args=['--input-rna',str(input_dir/'rna.h5ad'),'--input-atac',str(input_dir/'atac.h5ad'),
          '--prior',row.graph_path]
    for k,v in SHARED.items(): args.extend(['--'+k.replace('_','-'),str(v)])
    args.extend(['--random-seed',str(row.model_seed),'--train-dir',str(output)])
    if not smoke: args.append('--require-converge')
    for modality in ['rna','atac','feature']:
        args.extend(['--output-'+modality,str(output/(modality+'_latent.csv'))])
    args.extend(['--run-info',str(output/'run_info.yaml')])
    return args


def smoke_fit_limits(stage):
    # Original cluster matching needs an informative pretrained representation;
    # two pretraining epochs can yield all-zero matches at the unchanged cutoff.
    return dict(max_epochs=50 if stage=='pretrain' else 2,patience=None,reduce_lr_patience=None)


def checked_balancer(original):
    import numpy as np
    @functools.wraps(original)
    def check(*data,**kw):
        original(*data,**kw)
        for modality in data:
            weights=modality.obs[kw.get('key_added','balancing_weight')].to_numpy()
            if not np.isfinite(weights).all() or (weights<0).any() or weights.sum()<=0:
                raise ValueError('Original balancing weights are nonfinite/empty; pretraining must establish matches before fine-tuning')
    return check


def check_outputs(output,row,expected_ids,vertices):
    import pandas as pd
    import numpy as np
    for kind,ids in list(expected_ids.items())+[('feature',vertices)]:
        frame=pd.read_csv(output/(kind+'_latent.csv'),index_col=0,header=None)
        if not frame.index.is_unique or set(frame.index)!=set(ids) or frame.shape!=(len(ids),50) or not np.isfinite(frame.to_numpy()).all():
            raise ValueError('Invalid saved embedding '+kind)
    if any(output.glob('*gate*')):
        raise ValueError('GCN run unexpectedly produced gate artifacts')
    import scglue.models
    model=scglue.models.load_model(output/'final.dill')
    proof=verify_model(model)
    if model.random_seed!=row.model_seed or set(model.vertices)!=set(vertices):
        raise ValueError('Checkpoint seed/vertices do not match manifest')
    for stage in ['pretrain','fine-tune']:
        if not (output/stage/'final.dill').is_file(): raise ValueError('Missing stage checkpoint')
    return proof


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-id',type=int)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--smoke-cells',type=int,default=256)
    args=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'): parser.error('Training requires a Slurm compute-node allocation')
    if not args.smoke and args.task_id is None: parser.error('--task-id required')
    frozen=verify_freeze();manifest=validate_manifest()
    task=0 if args.smoke else args.task_id
    if task not in range(3): parser.error('Task ID must be 0..2')
    row=next(r for r in manifest.itertuples(index=False) if r.task_id==task)
    if not args.smoke:
        proof=json.loads((EXPERIMENT/'validation/smoke_success.json').read_text())
        if proof['status']!='passed' or proof['frozen_inputs_sha256']!=sha(EXPERIMENT/'validation/frozen_inputs.json'):
            raise ValueError('Full training requires successful smoke validation of these frozen inputs')
    output=EXPERIMENT/'smoke'/('job_'+os.environ['SLURM_JOB_ID'])/'run' if args.smoke else Path(row.run_dir)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.mkdir()  # Refuse to overwrite any existing run, including failed outputs.
    shutil.copyfile(EXPERIMENT/'manifest.csv',output/'manifest.csv')
    source_input=INPUT
    scglue=use_original()
    import anndata as ad
    import numpy as np
    import networkx as nx
    import scglue.models
    if args.smoke:
        if args.smoke_cells<=100: parser.error('Smoke needs >100 cells for unchanged 100D preprocessing')
        source_input=output.parent/'inputs';source_input.mkdir()
        rna=ad.read_h5ad(INPUT/'rna.h5ad',backed='r')
        atac=ad.read_h5ad(INPUT/'atac.h5ad',backed='r')
        common=rna.obs_names.intersection(atac.obs_names)
        rng=np.random.RandomState(0)
        ids=common.take(np.sort(rng.choice(len(common),args.smoke_cells,replace=False)))
        for modality,data in [('rna',rna),('atac',atac)]:
            # Slice backed input to memory; original data are never modified.
            data[ids].to_memory().write_h5ad(source_input/(modality+'.h5ad'))
            data.file.close()
    original_cls=scglue.models.SCGLUEModel
    original_fit=original_cls.fit
    original_balance=scglue.data.estimate_balancing_weight
    constructed=[]
    def audited_constructor(*a,**kw):
        model=original_cls(*a,**kw)
        constructed.append(verify_model(model))
        print('AUDITED ORIGINAL GCN: '+json.dumps(constructed[-1]),flush=True)
        return model
    def bounded_smoke_fit(self,*a,**kw):
        verify_model(self)
        kw.update(smoke_fit_limits(Path(kw['directory']).name))
        return original_fit(self,*a,**kw)
    namespace=runpy.run_path(str(ORIGINAL/'evaluation/workflow/scripts/run_GLUE.py'),run_name='original_glue_runner')
    command=runner_arguments(row,output,source_input,args.smoke)
    oldargv=sys.argv
    sys.argv=[str(ORIGINAL/'evaluation/workflow/scripts/run_GLUE.py')]+command
    scglue.models.SCGLUEModel=audited_constructor
    scglue.data.estimate_balancing_weight=checked_balancer(original_balance)
    if args.smoke: original_cls.fit=bounded_smoke_fit
    started=time.time()
    try:
        parsed=namespace['parse_args']()
        namespace['main'](parsed)
    finally:
        scglue.models.SCGLUEModel=original_cls
        original_cls.fit=original_fit
        scglue.data.estimate_balancing_weight=original_balance
        sys.argv=oldargv
    if len(constructed)!=2: raise ValueError('Expected original pretrain and fine-tune GCN constructions')
    expected={}
    for m in ['rna','atac']:
        data=ad.read_h5ad(source_input/(m+'.h5ad'),backed='r')
        expected[m]=data.obs_names.tolist();data.file.close()
    graph=nx.read_graphml(row.graph_path)
    proof=check_outputs(output,row,expected,list(graph))
    graph_info=json.loads((EXPERIMENT/'validation/graph_verification.json').read_text())[row.condition]
    saved=info(output/'run_info.yaml')
    saved.update(architecture='original_glue_gcn',original_repository=str(ORIGINAL),
        original_prior=frozen['original_repository']+'/evaluation/results_gcn_h100/raw/10x-Multiome-Pbmc10k/original/gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/sub.graphml.gz',
        graph_perturbation=row.graph_perturbation,graph_seed=0,graph_swap_multiplier=10.,graph_retain_fraction=float(row.retain_fraction),
        graph_perturbation_metadata=graph_info['metadata'],condition=row.condition,model_seed=int(row.model_seed),
        graph_file_sha256=sha(row.graph_path),original_source_sha256=frozen['original_source_sha256'],
        architecture_verification=proof,construction_audits=constructed,slurm_job_id=os.environ['SLURM_JOB_ID'],
        evaluation_mode='smoke' if args.smoke else 'full',smoke_max_epochs_per_stage={'pretrain':50,'fine-tune':2} if args.smoke else None,
        frozen_inputs_sha256=sha(EXPERIMENT/'validation/frozen_inputs.json'),elapsed_seconds=time.time()-started,
        original_runner_argv=command,training_wrapper_sha256=sha(Path(__file__).resolve()))
    import yaml
    (output/'run_info.yaml').write_text(yaml.safe_dump(saved,sort_keys=True))
    save_json(output/'architecture_verification.json',proof)
    save_json(output/'completion.json',dict(status='complete',smoke=args.smoke,task_id=task,run_dir=str(output),
                  embedding_shapes={m:[len(ids),50] for m,ids in expected.items()},architecture=proof))
    if args.smoke:
        save_json(EXPERIMENT/'validation/smoke_training.json',dict(status='training_passed',run_dir=str(output),
                  frozen_inputs_sha256=sha(EXPERIMENT/'validation/frozen_inputs.json'),job_id=os.environ['SLURM_JOB_ID']))
    print('GCN TRAINING COMPLETE: '+str(output),flush=True)


if __name__=='__main__':main()
