"""Strict matched architecture-by-size analysis; no training or unirep computation."""
import csv,itertools,json,subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]; REPO=R.parents[1]
rows=list(csv.DictReader((R/'manifests/architecture_by_size_manifest.csv').open()))
full={r['architecture']:r for r in rows if r['cell_label']=='full'}
assert len(rows)==30 and len(full)==3
metrics=['mean_average_precision','normalized_mutual_info','avg_silhouette_width','avg_silhouette_width_batch','graph_connectivity','foscttm','neighbor_conservation','feature_consistency','seurat_alignment_score','runtime']
records=[]
for r in rows:
 out=Path(r['output_directory']); ids=Path(r['cell_manifest_path']).read_text().splitlines()
 for mod in ('rna','atac'):
  latent=pd.read_csv(out/f'{mod}_latent.csv',header=None,index_col=0)
  assert latent.index.tolist()==ids and latent.shape==(len(ids),50) and np.isfinite(latent.values).all()
 m=yaml.safe_load((out/'cell_integration.yaml').read_text())
 # Keep derived feature metrics separate from all existing run outputs.
 dest=R/'metrics'/f"{r['run_id']}_feature_consistency.yaml"
 subprocess.run([str(REPO/'conda/bin/python'),str(REPO/'evaluation/workflow/scripts/feature_consistency.py'),'-q',str(out/'feature_latent.csv'),'-r',str(Path(full[r['architecture']]['output_directory'])/'feature_latent.csv'),'-o',str(dest)],check=True)
 m.update(yaml.safe_load(dest.read_text()))
 m['runtime']=float(yaml.unsafe_load((out/'run_info.yaml').read_text())['time'])
 assert all(np.isfinite(m[k]) for k in metrics)
 m.update({k:r[k] for k in ('run_id','architecture','subsample_seed','cell_manifest_path')});m['cell_count']=int(r['cell_count']);records.append(m)
df=pd.DataFrame(records)
for (size,seed),group in df[df.cell_count<32231].groupby(['cell_count','subsample_seed']):
 assert set(group.architecture)=={'gcn','gat','gated'} and group.cell_manifest_path.nunique()==1
 paths=[json.loads((Path(next(r['output_directory'] for r in rows if r['run_id']==rid))/'unirep_inputs.json').read_text()) for rid in group.run_id]
 assert paths[0]==paths[1]==paths[2]
df.to_csv(R/'metrics/architecture_by_size_by_run.csv',index=False)
sub=df[df.cell_count<32231]
summary=sub.groupby(['cell_count','architecture'])[metrics].agg(['count','mean','std'])
assert (summary.xs('count',axis=1,level=1)==3).all().all()
summary.to_csv(R/'metrics/architecture_by_size_summary.csv')
deltas=[]
for size,g in sub.groupby('cell_count'):
 for a,b in itertools.combinations(('gcn','gat','gated'),2):
  x=g[g.architecture==a].set_index('subsample_seed');y=g[g.architecture==b].set_index('subsample_seed')
  for seed in ('0','1','2'):
   deltas.append(dict(cell_count=size,comparison=f'{a}-{b}',subsample_seed=seed,**{k:x.loc[seed,k]-y.loc[seed,k] for k in metrics}))
delta=pd.DataFrame(deltas);delta.to_csv(R/'metrics/architecture_by_size_paired_differences.csv',index=False)
delta.groupby(['cell_count','comparison'])[metrics].agg(['mean','std']).to_csv(R/'metrics/architecture_by_size_paired_summary.csv')
scaling=df.groupby(['cell_count','architecture']).runtime.agg(['count','mean','std']).reset_index();scaling.to_csv(R/'analysis/architecture_runtime_scaling.csv',index=False)
for arch,g in scaling.groupby('architecture'):
 plt.errorbar(g.cell_count,g['mean']/3600,yerr=g['std'].fillna(0)/3600,marker='o',label=arch.upper())
plt.xticks([8000,16000,24000,32231]);plt.xlabel('Paired cells');plt.ylabel('Training runtime (hours)');plt.legend();plt.tight_layout();plt.savefig(R/'analysis/architecture_runtime_scaling.png',dpi=250);plt.close()
lines=['# Matched SHARE-seq architecture-by-size results','','All subsample entries are mean ± sample SD (ddof=1), n=3 matched cell subsets; model seed=0. Full-data runtime uses one existing primary run per architecture (no SD). Runtime is run_info.yaml time, in seconds. Feature consistency compares each subset with its same-architecture full-data model using the canonical 2,000-feature, four-repeat, seed-0 metric. Neighbor conservation is the existing unimodal-neighborhood consistency metric.','','| Cells | Architecture | '+' | '.join(metrics)+' |','|---|---|'+'---|'*len(metrics)]
for (size,arch),s in summary.iterrows():lines.append(f'| {size} | {arch.upper()} | '+' | '.join(f'{s[(k,"mean")]:.6g} ± {s[(k,"std")]:.6g}' for k in metrics)+' |')
lines+=['','## Runtime scaling','','| Cells | Architecture | n | Seconds, mean ± SD |','|---|---|---|---|']
for _,s in scaling.iterrows():lines.append(f'| {s.cell_count} | {s.architecture} | {s["count"]} | {s["mean"]:.6g}'+(f' ± {s["std"]:.6g}' if s['count']>1 else ' (single run)')+' |')
lines+=['','![Runtime scaling](../analysis/architecture_runtime_scaling.png)','','Paired seed differences and their mean/SD are in `../metrics/architecture_by_size_paired_summary.csv`. Three subsamples quantify cell-selection variability, not model-initialization variability.']
(R/'reports/architecture_by_size_report.md').write_text('\n'.join(lines)+'\n')
print('Validated all 30 runs and nine matched triplets; architecture-by-size report complete.')
