#!/usr/bin/env python
"""Original GCN evaluation using the existing PBMC metric functions, without gates."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
from sklearn import config_context

from common import (WORKTREE,EXPERIMENT,GATED,CONDITIONS,SHARED,INPUT,PRIOR,info,sha,
                    save_json,validate_manifest,verify_freeze,use_original,verify_model)

# Original source is loaded before the shared evaluator adjusts import paths.
use_original()
sys.path.insert(0,str(GATED/'scripts'))
import evaluate as core
import reporting as shared_report


def validate_run(row,metadata,obs):
    import scglue.models
    if metadata.get('architecture')!='original_glue_gcn': raise ValueError('Missing verified original GCN provenance')
    if metadata['args']['random_seed']!=row.model_seed or metadata['graph_seed']!=0 or metadata['condition']!=row.condition:
        raise ValueError('Run/manifest disagreement')
    if any(metadata['args'][k]!=v for k,v in SHARED.items()): raise ValueError('Run training settings differ')
    if Path(metadata['args']['prior']).resolve()!=Path(row.graph_path).resolve() or sha(row.graph_path)!=metadata['graph_file_sha256']:
        raise ValueError('Run guidance graph differs')
    if Path(metadata['original_prior']).resolve()!=PRIOR.resolve(): raise ValueError('Wrong original graph')
    run=Path(row.run_dir)
    if not (run/'completion.json').is_file(): raise ValueError('Training output is incomplete')
    model=scglue.models.load_model(run/'final.dill')
    proof=verify_model(model)
    if model.random_seed!=row.model_seed: raise ValueError('Saved checkpoint model seed differs')
    import networkx as nx
    graph=nx.read_graphml(row.graph_path)
    if set(model.vertices)!=set(graph): raise ValueError('Checkpoint vertex set differs')
    for m in ['rna','atac']:
        core.read_embedding(run/(m+'_latent.csv'),obs[m].index,50)
    core.read_embedding(run/'feature_latent.csv',list(graph),50)
    if any(run.glob('*gate*')): raise ValueError('GCN output must not contain gate diagnostics')
    return proof


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['full','smoke','preflight','report'],default='preflight')
    p.add_argument('--output',type=Path)
    p.add_argument('--smoke-run',type=Path)
    p.add_argument('--references-dir',type=Path,default=GATED/'reports/full/references')
    options=p.parse_args()
    if options.mode=='full' and not os.environ.get('SLURM_JOB_ID'): p.error('Full evaluation requires a CPU Slurm allocation')
    output=options.output or EXPERIMENT/'reports'/options.mode
    output=output.resolve()
    if (EXPERIMENT/'results').resolve() in output.parents or INPUT.resolve() in output.parents:
        p.error('Output must not be inside training or raw-input directories')
    output.mkdir(parents=True,exist_ok=True)
    if options.mode=='report':
        from gcn_report import generate
        generate(output)
        return
    frozen=verify_freeze();manifest=validate_manifest()
    settings=json.loads((GATED/'reports/full/evaluation_config.json').read_text())
    # Copy actual completed GATED evaluation parameters, rather than merely assume defaults.
    keys=['cell_type','evaluation_seed','chunk_size','working_memory_mb','cross_k','lisi_perplexity','kbet_k','leiden_resolution','smoke_cells']
    params={k:settings[k] for k in keys}
    args=SimpleNamespace(**params,mode='smoke' if options.mode=='smoke' else 'full',references='existing')
    if options.mode=='smoke':
        if options.smoke_run is None: p.error('--smoke-run required')
        metadata=info(options.smoke_run/'run_info.yaml')
        row=SimpleNamespace(**manifest.iloc[0].to_dict());row.run_dir=str(options.smoke_run)
        selected=[row];inputs={m:Path(metadata['args']['input_'+m]) for m in ['rna','atac']}
    else:
        selected=list(manifest.itertuples(index=False));inputs={m:INPUT/(m+'.h5ad') for m in ['rna','atac']}
    obs={m:core.read_obs(path) for m,path in inputs.items()}
    paired=core.verify_pairs(obs['rna'],obs['atac'],WORKTREE/'data/collect/10x-Multiome-Pbmc10k.ipynb')
    save_json(output/'pairing_verification.json',paired)
    save_json(output/'dataset_metadata.json',{m:dict(n_cells=len(o),cell_type_counts=o[params['cell_type']].astype(str).value_counts().to_dict()) for m,o in obs.items()})
    versions={}
    for pkg in ['numpy','pandas','scipy','scikit-learn','scanpy','anndata','torch','leidenalg','matplotlib']:
        versions[pkg]=importlib.metadata.version(pkg)
    fingerprints={}
    for row in selected:
        run=Path(row.run_dir)
        for file in ['run_info.yaml','architecture_verification.json','completion.json','rna_latent.csv','atac_latent.csv','feature_latent.csv','final.dill','manifest.csv']:
            fingerprints[str(run/file)]=sha(run/file)
    config=dict(architecture='original_glue_gcn',evaluation_mode=options.mode,parameters=params,versions=versions,
        frozen_inputs_sha256=sha(EXPERIMENT/'validation/frozen_inputs.json'),run_inputs_sha256=fingerprints,
        metric_core_sha256=sha(GATED/'scripts/evaluate.py'),figure_core_sha256=sha(GATED/'scripts/reporting.py'),
        gcn_evaluator_sha256=sha(Path(__file__).resolve()),gcn_report_sha256=sha(Path(__file__).with_name('gcn_report.py')),
        completed_gated_evaluation_fingerprint=settings['fingerprint'],paired=paired,
        reference_files_sha256={str(path):sha(path) for path in options.references_dir.glob('*_unirep.h5ad')} if options.mode!='smoke' else {})
    digest=__import__('hashlib').sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    config['fingerprint']=digest
    previous=output/'evaluation_config.json'
    if previous.exists() and json.loads(previous.read_text()).get('fingerprint')!=digest:
        raise ValueError('Evaluation inputs/config changed; choose a new --output')
    save_json(previous,config)
    audits=[]
    for row in selected:
        metadata=info(Path(row.run_dir)/'run_info.yaml')
        audits.append(dict(task_id=int(row.task_id),condition=row.condition,model_seed=int(row.model_seed),proof=validate_run(row,metadata,obs)))
    save_json(output/'architecture_audit.json',audits)
    if options.mode=='preflight':
        save_json(output/'status.json',dict(status='preflight_complete',n_validated_runs=len(audits)))
        return
    save_json(output/'status.json',dict(status='running',slurm_job_id=os.environ.get('SLURM_JOB_ID')))
    references=[None,None]
    if options.mode=='full':
        expected=json.loads((GATED/'reports/full/reference_provenance.json').read_text())
        known=list(expected['files'].values())
        if len(config['reference_files_sha256'])!=2 or any(h not in known for h in config['reference_files_sha256'].values()):
            raise ValueError('Require the exact completed GATED evaluation PCA/LSI references')
        references=core.make_references(options.references_dir,output,args,obs)
        save_json(output/'reference_provenance.json',config['reference_files_sha256'])
    records=[];graph_names=[]
    with config_context(working_memory=params['working_memory_mb']):
        for row in selected:
            checkpoint=output/'checkpoints'/('task_{}.json'.format(row.task_id))
            if checkpoint.exists():
                record=json.loads(checkpoint.read_text())
                if record['fingerprint']!=digest: raise ValueError('Stale metric checkpoint')
            else:
                metadata=info(Path(row.run_dir)/'run_info.yaml')
                # The shared graph evaluator expects the original source prior;
                # keep the training metadata untouched and adapt an in-memory copy.
                adapted=dict(metadata,args=dict(metadata['args'],prior=metadata['original_prior']))
                graph,statistics=core.reconstruct_graph(adapted)
                print('Evaluating ORIGINAL GCN task {}: {} seed {}'.format(row.task_id,row.condition,row.model_seed),flush=True)
                record=core.evaluate_run(row,metadata,obs,paired,graph,statistics,references,args,include_gates=False)
                graph_names=list(statistics)
                if any(k.startswith('gate_') for k in record['metrics']): raise ValueError('GCN evaluation emitted gate metrics')
                record['fingerprint']=digest;save_json(checkpoint,record)
            records.append(record)
    names=sorted(records[0]['metrics'])
    meta=['condition','model_seed','graph_seed','task_id','evaluation_mode','run_dir']
    frame=pd.DataFrame([dict(**r['metadata'],**r['metrics']) for r in records])[meta+names]
    frame.to_csv(output/'per_run_metrics.csv',index=False,na_rep='N/A')
    summary,comparison=core.aggregate(frame,names)
    summary.to_csv(output/'summary_metrics.csv',index=False,na_rep='N/A')
    comparison.to_csv(output/'baseline_comparison.csv',index=False,na_rep='N/A')
    if not graph_names:
        metadata=info(Path(selected[0].run_dir)/'run_info.yaml')
        _,statistics=core.reconstruct_graph(dict(metadata,args=dict(metadata['args'],prior=metadata['original_prior'])))
        graph_names=list(statistics)
    frame[['condition','model_seed','graph_seed']+graph_names].to_csv(output/'graph_statistics.csv',index=False,na_rep='N/A')
    pd.DataFrame([a for r in records for a in r['availability']]).to_csv(output/'metric_availability.csv',index=False)
    from gcn_report import generate
    generate(output)
    save_json(output/'status.json',dict(status='smoke_complete' if options.mode=='smoke' else 'complete',
        n_evaluated_runs=len(records),slurm_job_id=os.environ.get('SLURM_JOB_ID')))
    if options.mode=='smoke':
        training=json.loads((EXPERIMENT/'validation/smoke_training.json').read_text())
        if Path(training['run_dir']).resolve()!=options.smoke_run.resolve(): raise ValueError('Smoke training/evaluation run mismatch')
        training.update(status='passed',evaluation_output=str(output),evaluation_supports_gcn_without_gates=True)
        save_json(EXPERIMENT/'validation/smoke_success.json',training)
    print('Original GCN evaluation/report completed: '+str(output),flush=True)


if __name__=='__main__':main()
