"""Frozen configuration and read-only validation for original GCN-GLUE."""
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
import yaml

WORKTREE = Path('/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC')
EXPERIMENT = WORKTREE/'evaluation/pbmc_graph_subsampling_gcn'
ORIGINAL = Path('/project/6001426/paa40/GlUE_Exp/GLUE')
ENVIRONMENT = ORIGINAL/'conda'
INPUT = ORIGINAL/'evaluation/results_gcn_h100/raw/10x-Multiome-Pbmc10k/original'
PRIOR = INPUT/'gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/sub.graphml.gz'
GATED = WORKTREE/'evaluation/pbmc_graph_perturbation'
DATASET = '10x-Multiome-Pbmc10k'
CONDITIONS = ['original','retain_75','retain_50','retain_25','retain_10']
FRACTIONS = [1.,.75,.5,.25,.1]
SHARED = dict(dim=50,alt_dim=100,hidden_depth=2,hidden_dim=256,dropout=.2,
              lam_graph=.02,lam_align=.05,lr=.002,neg_samples=10,val_split=.1,
              data_batch_size=128,balance_res=1.,balance_cutoff=.5,balance_power=4.)


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor('tag:yaml.org,2002:python/object/apply:pathlib.PosixPath',
                       lambda loader,node:str(Path(*loader.construct_sequence(node))))


def info(path):
    with Path(path).open() as f: return yaml.load(f,Loader=Loader)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def save_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')
    temp.replace(path)


def edge_digest(graph,biological_only=False):
    edges=sorted((str(u),str(v),dict(d)) for u,v,d in graph.edges(data=True)
                 if not biological_only or (u!=v and d['type']=='fwd'))
    return hashlib.sha256(json.dumps(edges,sort_keys=True).encode()).hexdigest()


def original_sources():
    files=list((ORIGINAL/'scglue').rglob('*.py'))
    files.append(ORIGINAL/'evaluation/workflow/scripts/run_GLUE.py')
    return {str(p):sha(p) for p in sorted(files)}


def validate_manifest(path=EXPERIMENT/'manifest.csv'):
    frame=pd.read_csv(path)
    required=['task_id','condition','graph_perturbation','retain_fraction','graph_seed','model_seed','graph_path','run_dir']
    if list(frame.columns)!=required or len(frame)!=15:
        raise ValueError('Expected exact 15-row GCN manifest schema')
    for index,row in enumerate(frame.itertuples(index=False)):
        c=CONDITIONS[index//3]
        expected=dict(task_id=index,condition=c,graph_perturbation='none' if index<3 else 'subsample',
                      retain_fraction=FRACTIONS[index//3],graph_seed=0,model_seed=index%3,
                      graph_path=str(EXPERIMENT/'graphs'/(c+'.graphml.gz')),
                      run_dir=str(EXPERIMENT/'results'/DATASET/c/'graph_seed:0'/('model_seed:'+str(index%3))))
        if row._asdict()!=expected: raise ValueError('Incorrect manifest row {}'.format(index))
    return frame


def verify_freeze():
    frozen=json.loads((EXPERIMENT/'validation/frozen_inputs.json').read_text())
    if original_sources()!=frozen['original_source_sha256']:
        raise ValueError('Original GLUE source changed after validation; refuse training/evaluation')
    if sha(WORKTREE/'evaluation/workflow/scripts/graph_perturbation.py')!=frozen['perturbation_code_sha256']:
        raise ValueError('Perturbation implementation changed')
    if sha(EXPERIMENT/'manifest.csv')!=frozen['manifest_sha256']:
        raise ValueError('Manifest changed')
    if SHARED!=frozen['shared_training_settings']:
        raise ValueError('Shared training settings changed')
    for filename,digest in frozen['graph_file_sha256'].items():
        if sha(filename)!=digest: raise ValueError('Prepared guidance graph changed')
    if sha(PRIOR)!=frozen['original_prior_sha256']:
        raise ValueError('Original guidance graph changed')
    for filename,identity in frozen['raw_inputs'].items():
        p=Path(filename)
        if dict(size=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns)!=identity:
            raise ValueError('Raw input changed')
    return frozen


def use_original():
    """Put original source first, and reject a cached alternate scglue package."""
    sys.path.insert(0,str(ORIGINAL))
    import scglue
    if ORIGINAL.resolve() not in Path(scglue.__file__).resolve().parents:
        raise RuntimeError('Wrong scglue import: '+scglue.__file__)
    return scglue


def verify_model(model):
    import inspect
    from scglue.models import sc,nn
    if type(model.net.g2v) is not sc.GraphEncoder or type(model.net.g2v.conv) is not nn.GraphConv:
        raise ValueError('Model must instantiate original GraphEncoder with GraphConv')
    if type(model.net.v2g) is not sc.GraphDecoder:
        raise ValueError('Original graph decoder required')
    paths=[Path(inspect.getfile(cls)).resolve() for cls in [type(model),type(model.net.g2v),type(model.net.g2v.conv),type(model.net.v2g)]]
    if not all(ORIGINAL.resolve() in p.parents for p in paths):
        raise ValueError('Model classes must originate in original GLUE repository')
    if any('gate' in n.lower() or 'attention' in n.lower() for n,_ in model.net.named_parameters()):
        raise ValueError('Original GLUE cannot have gate/attention parameters')
    if hasattr(model.net.g2v,'gate_logits'):
        raise ValueError('Learnable edge gates are forbidden')
    if any(d['prob_model']!='NB' for d in model.domains.values()):
        raise ValueError('Expected original NB likelihoods for both modalities')
    return dict(model_class=type(model).__module__+'.'+type(model).__name__,
                graph_encoder=type(model.net.g2v).__module__+'.'+type(model.net.g2v).__name__,
                graph_convolution=type(model.net.g2v.conv).__module__+'.'+type(model.net.g2v.conv).__name__,
                source_files=[str(p) for p in paths],model_seed=int(model.random_seed),
                graph_parameters={n:list(v.shape) for n,v in model.net.g2v.named_parameters()},
                learned_edge_gates=False,attention=False)
