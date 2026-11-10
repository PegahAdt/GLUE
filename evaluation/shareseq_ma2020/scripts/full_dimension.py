#!/usr/bin/env python
"""Isolated full-data dimension sweep: immutable inputs and fail-closed reuse."""
import argparse, csv, hashlib, json, os, shlex, subprocess
from pathlib import Path
import h5py
import numpy as np
import pandas as pd
import yaml
R=Path(__file__).resolve().parents[1]
REPO=R.parents[1]
MAN=R/'manifests/full_dimension_comparison_manifest.csv'
AUDIT=R/'analysis/full_dimension_preflight.json'
DIMS=[16,32,50,64,100,128,200,256,384,512,768,1024]
ARCH=['gcn','gat','gated']
FIXED=dict(alt_dim=100,hidden_depth=2,hidden_dim=256,dropout=.2,lam_graph=.02,lam_align=.05,lr=.002,neg_samples=10,data_batch_size=128,random_seed=0,require_converge=True,val_split=.1,balance_cutoff=.5,balance_power=4.,balance_res=1.)
METRICS={'mean_average_precision':'MAP','normalized_mutual_info':'NMI','avg_silhouette_width':'ASW','avg_silhouette_width_batch':'Batch ASW','graph_connectivity':'Graph connectivity','foscttm':'FOSCTTM','neighbor_conservation':'Neighbor conservation','seurat_alignment_score':'Seurat alignment'}
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
 return h.hexdigest()
def rows(): return list(csv.DictReader(MAN.open()))
def save(rs):
 tmp=MAN.with_suffix('.tmp');
 with tmp.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0])); w.writeheader(); w.writerows(rs)
 tmp.replace(MAN)
def info(r): return yaml.unsafe_load((Path(r['output_directory'])/'run_info.yaml').read_text())
def ordered(p,ids):
 with h5py.File(p) as f:
  obs=f['obs']; assert obs[obs.attrs['_index']].asstr()[:].tolist()==ids,str(p)
def validate(r):
 out=Path(r['output_directory']); ids=Path(r['cell_manifest_path']).read_text().splitlines(); d=int(r['latent_dim'])
 for name in ['final.dill','run_info.yaml','requested_configuration.json','rna_latent.csv','atac_latent.csv','feature_latent.csv']:
  assert (out/name).is_file() and (out/name).stat().st_size,name
 a=info(r)['args']
 for k,v in dict(FIXED,dim=d,random_seed=int(r['model_seed'])).items(): assert a[k]==v,(r['run_id'],k,a.get(k),v)
 if r['architecture']!='gcn': assert a['graph_encoder']==r['architecture']
 if r['architecture']=='gat': assert a['gat_negative_slope']==.2 and 'GLUE_GAT/' in info(r)['cmd']
 if r['architecture']=='gated': assert a['gate_init']==float(r['gate_init']) and a['lam_keep']==0 and 'GLUE_GATED/' in info(r)['cmd']
 assert Path(a['prior']).resolve()==Path(r['graph_path']).resolve()
 stamp=json.loads((out/'requested_configuration.json').read_text())
 for k in ['architecture','model_seed','latent_dim','graph_checksum','gate_init','lam_keep','gat_negative_slope']: assert str(stamp[k])==r[k],k
 assert sha(r['graph_path'])==r['graph_checksum']
 for m in ['rna','atac']:
  ordered(out/f'{m}.h5ad',ids)
  x=pd.read_csv(out/f'{m}_latent.csv',header=None,index_col=0)
  assert x.shape==(32231,d) and x.index.tolist()==ids and np.isfinite(x.values).all()
 x=pd.read_csv(out/'feature_latent.csv',header=None,index_col=0)
 assert x.shape[1]==d and np.isfinite(x.values).all()
 assert float(info(r)['time'])>0
 return float(info(r)['time'])
def preflight():
 master=list(csv.DictReader((R/'manifests/master_experiment_manifest.csv').open()))
 rs=[]; audit={'runs':[]}; ids=(R/'manifests/cells_sizefull.txt').read_text().splitlines()
 assert len(ids)==len(set(ids))==32231
 for arch in ARCH:
  base=next(r for r in master if r['architecture']==arch and r['cell_label']=='full' and r['model_seed']=='0' and (arch!='gated' or r['gate_init']=='0.95'))
  runtime=validate(base)
  for dim in DIMS:
   r=base.copy(); r.update(latent_dim=str(dim),reuse_source=base['run_id'] if dim==50 else '',replicate_source='reused_validated' if dim==50 else 'full_dimension_comparison',training_state='reused_validated' if dim==50 else 'missing',metric_state='pending',runtime=str(runtime) if dim==50 else '',slurm_job_id='')
   if dim!=50:
    rid=f'{arch}_sizefull_dim{dim}_model0'+('_gate0.95' if arch=='gated' else '')
    out=R/'results'/rid; r.update(run_id=rid,output_directory=str(out),expected_checkpoint=str(out/'final.dill'))
    if out.exists():
     r['runtime']=str(validate(r)); r.update(training_state='reused_validated',reuse_source=rid)
    impl=REPO if arch=='gcn' else REPO.parent/('GLUE_'+arch.upper())
    r['git_commit']=subprocess.check_output(['git','-C',str(impl),'rev-parse','HEAD'],text=True).strip()
   rs.append(r)
 for key in ['cell_manifest_path','graph_path','graph_checksum','rna_path','atac_path']: assert len({r[key] for r in rs})==1,key
 for m in ['rna','atac']: ordered(rs[0][m+'_path'],ids)
 assert len(rs)==36 and len({(r['architecture'],r['latent_dim']) for r in rs})==36
 assert sum(r['latent_dim']=='50' and r['training_state']=='reused_validated' for r in rs)==3
 audit['missing_rows']=[i for i,r in enumerate(rs) if r['training_state']=='missing']
 audit['input_hashes']={str(p):sha(p) for p in [Path(rs[0][k]) for k in ['cell_manifest_path','graph_path','rna_path','atac_path']]}
 audit['unireps']=json.loads((R/'results/gcn_sizefull_model0/unirep_inputs.json').read_text())
 from unirep_cache import validate_rep
 import anndata as ad
 for m,p in audit['unireps'].items():
  x=ad.read_h5ad(rs[0][m+'_path'],backed='r')
  try: validate_rep(Path(p),x,ids)
  finally: x.file.close()
 audit['unirep_hashes']={p:sha(p) for p in audit['unireps'].values()}
 for arch in ARCH:
  impl=REPO if arch=='gcn' else REPO.parent/('GLUE_'+arch.upper())
  env=os.environ.copy(); env.update(PYTHONPATH=str(impl),PYTHONNOUSERSITE='1')
  resolved=subprocess.check_output([str(REPO/'conda/bin/python'),'-c','import scglue; print(scglue.__file__)'],cwd=R,env=env,text=True).strip()
  assert Path(resolved).resolve()==(impl/'scglue/__init__.py').resolve(),resolved
  audit[arch+'_scglue']=resolved
  audit[arch+'_code_hashes']={str(p):sha(p) for p in [impl/'evaluation/workflow/scripts/run_GLUE.py',*sorted((impl/'scglue').rglob('*.py'))]}
 save(rs); AUDIT.write_text(json.dumps(audit,indent=2)+'\n')
 print(json.dumps({'configurations':len(rs),'reused':36-len(audit['missing_rows']),'missing_rows':audit['missing_rows'],'imports':{k:v for k,v in audit.items() if k.endswith('_scglue')}},indent=2))
def check(r):
 a=json.loads(AUDIT.read_text())
 for p,h in {**a['input_hashes'],**a[r['architecture']+'_code_hashes']}.items(): assert sha(p)==h,p
 for m in ['rna','atac']: ordered(Path(r['output_directory'])/f'{m}.h5ad',Path(r['cell_manifest_path']).read_text().splitlines())
def metrics(r):
 validate(r)
 a=json.loads(AUDIT.read_text()); out=Path(r['output_directory']); dest=R/'metrics/full_dimension'/r['run_id']; dest.mkdir(parents=True,exist_ok=True)
 for p,h in a['unirep_hashes'].items(): assert sha(p)==h,p
 old=out/'cell_integration.yaml'; record=out/'unirep_inputs.json'
 if old.exists() and record.exists() and json.loads(record.read_text())==a['unireps']:
  values=yaml.safe_load(old.read_text())
 else:
  target=dest/'cell_integration.yaml'
  env=os.environ.copy(); env.update(PYTHONPATH=str(REPO),PYTHONNOUSERSITE='1')
  subprocess.run([str(REPO/'conda/bin/python'),str(REPO/'evaluation/workflow/scripts/cell_integration.py'),'-d',a['unireps']['rna'],a['unireps']['atac'],'-l',str(out/'rna_latent.csv'),str(out/'atac_latent.csv'),'--cell-type','cell_type','--domain','domain','--paired','-o',str(target)],env=env,check=True)
  values=yaml.safe_load(target.read_text())
 assert set(values)==set(METRICS) and all(np.isfinite(v) for v in values.values())
 (dest/'cell_integration.yaml').write_text(yaml.safe_dump(values))
 (dest/'unirep_inputs.json').write_text(json.dumps(a['unireps'],indent=2))
 if r['architecture']=='gated':
  # Execute the canonical extraction implementation into an isolated directory.
  for n in ['final.dill']:
   p=dest/n
   if not p.exists(): p.symlink_to(out/n)
  env=os.environ.copy(); env.update(PYTHONPATH=str(REPO.parent/'GLUE_GATED'),PYTHONNOUSERSITE='1')
  subprocess.run([str(REPO/'conda/bin/python'),str(R/'scripts/extract_gates.py'),'--smoke',str(dest)],cwd=R,env=env,check=True)
  summary=yaml.safe_load((dest/'gate_summary.yaml').read_text()); summary['run_id']=r['run_id']; summary['latent_dim']=int(r['latent_dim'])
  (dest/'gate_summary.yaml').write_text(yaml.safe_dump(summary))
 (dest/'VALIDATED').write_text('Canonical metrics and gates validated\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('action',choices=['preflight','row','validate','check','stamp','metrics']); p.add_argument('index',type=int,nargs='?'); a=p.parse_args()
 if a.action=='preflight': preflight()
 else:
  r=rows()[a.index]; out=Path(r['output_directory'])
  if a.action=='row':
   for k,v in r.items(): print(f'{k}={shlex.quote(v)}')
  elif a.action=='validate': print(validate(r))
  elif a.action=='check': check(r)
  elif a.action=='stamp': (out/'requested_configuration.json').write_text(json.dumps(r,indent=2))
  elif a.action=='metrics': metrics(r)
