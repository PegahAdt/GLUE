#!/usr/bin/env python3
from pathlib import Path
import csv, yaml, os

ROOT=Path('/project/6001426/paa40/GlUE_Exp'); REPO=ROOT/'GLUE_GATED'
HERE=REPO/'evaluation/gate_init_sensitivity'; OUT=REPO/'evaluation/results_gate_init_sensitivity'
BASE=REPO/'evaluation/results_gated/raw/10x-Multiome-Pbmc10k'
PRIOR='gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0'
HP='dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10'
gates=(0.50,0.70,0.90,0.95,0.99); sizes=(250,2000,8000); seeds=(0,1,2)
job_id=os.environ.get('TRAINING_JOB_ID','')
HERE.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True); (HERE/'logs').mkdir(exist_ok=True)
expected={'graph_encoder':'gated','gate_init':0.95,'lam_keep':0.0,'dim':50,'alt_dim':100,'lr':0.002,
          'hidden_depth':2,'hidden_dim':256,'dropout':0.2,'lam_graph':0.02,'lam_align':0.05,
          'neg_samples':10,'data_batch_size':128,'random_seed':0}
rows=[]; tasks=[]
for size in sizes:
 for seed in seeds:
  old=BASE/f'subsample_size:{size}-subsample_seed:{seed}'/PRIOR/'GLUE'/HP/'seed:0'
  info=yaml.unsafe_load((old/'run_info.yaml').read_text()); args=info['args']
  bad={k:(args.get(k),v) for k,v in expected.items() if args.get(k)!=v}
  assert not bad,(size,seed,bad)
  assert f'subsample_size:{size}-subsample_seed:{seed}' in str(args['input_rna'])
  for f in ('rna_latent.csv','atac_latent.csv','feature_latent.csv','run_info.yaml','final.dill','gate_diagnostics.yaml'):
   assert (old/f).is_file() and (old/f).stat().st_size>0,(old,f)
  for gate in gates:
   if gate==0.95: path=old; source='REUSED_MATCHED_BASELINE'; state='REUSED_VALIDATED'
   else:
    path=OUT/f'gate_init:{gate:.2f}'/f'subsample_size:{size}-subsample_seed:{seed}'/'model_seed:0'
    source='NEW'; state='PLANNED'; tasks.append({'array_task_id':len(tasks),'gate_init':f'{gate:.2f}','subsample_size':size,'subsample_seed':seed,'model_seed':0,'result_path':str(path)})
   if source=='NEW' and job_id: state='SUBMITTED'
   rows.append({'architecture':'gated','gate_init':f'{gate:.2f}','subsample_size':size,'subsample_seed':seed,'model_seed':0,'dim':50,'result_path':str(path),'source':source,'job_id':job_id if source=='NEW' else '','array_task_id':'' if gate==0.95 else len(tasks)-1,'state':state,'exit_code':'0:0' if gate==0.95 else '','elapsed':''})
assert len(rows)==45 and len(tasks)==36
for name,data in [('all_configurations.csv',rows),('training_tasks.csv',tasks),('job_manifest.csv',rows)]:
 with (HERE/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
(HERE/'state.yaml').write_text(f'current_stage: {"training_submitted" if job_id else "ready_for_training"}\nconfiguration_count: 45\nreused_count: 9\nnew_training_count: 36\ntraining_job_ids: [{job_id}]\nmetric_job_ids: []\nfailed_tasks: []\nreport_status: not_started\n')
print('AUDIT_OK configurations=45 reused_0.95=9 new=36')
