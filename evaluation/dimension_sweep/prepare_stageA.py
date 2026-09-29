#!/usr/bin/env python3
"""Prepare and validate the isolated Stage-A dimension screen (small files only)."""
from pathlib import Path
import csv, re, os

ROOT=Path('/project/6001426/paa40/GlUE_Exp')
HERE=ROOT/'GLUE_GATED/evaluation/dimension_sweep'
OUT=ROOT/'GLUE_GATED/evaluation/results_dimension_sweep'
PRIOR='gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0'
HP='dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10'
BASE={
 'gcn':ROOT/'GLUE/evaluation/results_gcn_h100/raw/10x-Multiome-Pbmc10k',
 'gat':ROOT/'GLUE/evaluation/results_gat/raw/10x-Multiome-Pbmc10k',
 'gated':ROOT/'GLUE_GATED/evaluation/results_gated/raw/10x-Multiome-Pbmc10k'}

def run_dir(arch,size,seed):
 return BASE[arch]/f'subsample_size:{size}-subsample_seed:{seed}'/PRIOR/'GLUE'/HP/'seed:0'

def scalar(text,key):
 m=re.search(rf'^  {re.escape(key)}: (.+)$',text,re.M)
 return None if not m else m.group(1).strip()

reused=[]
for arch in ('gcn','gat','gated'):
 d=run_dir(arch,2000,0); p=d/'run_info.yaml'
 if not p.is_file(): raise SystemExit(f'missing reuse metadata: {p}')
 t=p.read_text()
 expected={'dim':'50','alt_dim':'100','data_batch_size':'128','dropout':'0.2','hidden_depth':'2','hidden_dim':'256','lam_align':'0.05','lam_graph':'0.02','lr':'0.002','neg_samples':'10','random_seed':'0','graph_encoder':arch}
 if arch=='gat': expected['gat_negative_slope']='0.2'
 if arch=='gated': expected.update(gate_init='0.95',lam_keep='0.0')
 bad={k:(scalar(t,k),v) for k,v in expected.items() if scalar(t,k)!=v}
 required=['rna_latent.csv','atac_latent.csv','feature_latent.csv','final.dill','metrics.yaml']
 missing=[x for x in required if not (d/x).is_file() or (d/x).stat().st_size==0]
 if bad or missing: raise SystemExit(f'invalid reuse {arch}: bad={bad} missing={missing}')
 reused.append({'stage':'A','architecture':arch,'dim':50,'size':2000,'subsample_seed':0,'model_seed':0,'result_path':str(d),'validation':'run_info exact match; required latents, final checkpoint, and metrics present'})

with (HERE/'reused_runs.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=reused[0]); w.writeheader(); w.writerows(reused)

tasks=[]
for arch in ('gcn','gat','gated'):
 for dim in (16,32,64,100):
  data=BASE['gcn']/f'subsample_size:2000-subsample_seed:0'
  dest=OUT/f'architecture:{arch}'/f'dim:{dim}'/'subsample_size:2000-subsample_seed:0'/'model_seed:0'
  tasks.append({'task_id':len(tasks),'stage':'A','architecture':arch,'dim':dim,'size':2000,'subsample_seed':0,'model_seed':0,'input_dir':str(data),'result_path':str(dest)})
with (HERE/'stageA_tasks.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=tasks[0]); w.writeheader(); w.writerows(tasks)

job_id=os.environ.get('STAGEA_JOB_ID','PENDING_SUBMISSION')
job_state='SUBMITTED' if job_id!='PENDING_SUBMISSION' else 'PLANNED'
fields=['stage','architecture','dim','size','subsample_seed','model_seed','job_id','array_task','state','exit_code','elapsed','result_path','reused','retry_job_id']
with (HERE/'job_manifest.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
 for r in reused: w.writerow({k:v for k,v in {**r,'job_id':'','array_task':'','state':'REUSED_VALIDATED','exit_code':'0:0','elapsed':'','reused':'true','retry_job_id':''}.items() if k in fields})
 for r in tasks: w.writerow({k:v for k,v in {**r,'job_id':job_id,'array_task':r['task_id'],'state':job_state,'exit_code':'','elapsed':'','reused':'false','retry_job_id':''}.items() if k in fields})

(HERE/'state.yaml').write_text(f'''current_stage: {'stage_A_submitted' if job_id!='PENDING_SUBMISSION' else 'stage_A_ready'}\ncompleted_configs:\n  - gcn_dim50_size2000_seed0_reused\n  - gat_dim50_size2000_seed0_reused\n  - gated_dim50_size2000_seed0_reused\npending_configs: 12\nfailed_configs: []\nsubmitted_job_ids: [{job_id if job_id!='PENDING_SUBMISSION' else ''}]\nmetric_job_ids: []\nselected_stageB_dimensions: {{}}\nselected_finalist_dimensions: {{}}\nfull_reference_status: not_started\nfinal_metric_status: not_started\nreport_status: not_started\n''')
print(f'validated reused={len(reused)} new_stageA={len(tasks)}')
