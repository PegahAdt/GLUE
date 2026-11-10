#!/usr/bin/env python
"""Scientific capacity-response tables and figures, with missing runs explicit."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from full_dimension import R,ARCH,DIMS,METRICS,rows,save,validate,info
p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');a=p.parse_args()
rs=rows(); data=[]; gates=[]
for r in rs:
 out=Path(r['output_directory']); dest=R/'metrics/full_dimension'/r['run_id']
 v=dict(run_id=r['run_id'],architecture=r['architecture'],latent_dim=int(r['latent_dim']),model_seed=0,feature_consistency=np.nan)
 v.update({m:np.nan for m in METRICS}); v.update(runtime_seconds=np.nan,gpu_peak_allocated_bytes=np.nan,gpu_peak_reserved_bytes=np.nan)
 if (out/'final.dill').exists():
  v['runtime_seconds']=validate(r); r['runtime']=str(v['runtime_seconds']);r['training_state']='reused_validated' if r['reuse_source'] else 'completed_validated'
  if (out/'resource_usage.json').exists():
   z=json.loads((out/'resource_usage.json').read_text());v.update(gpu_peak_allocated_bytes=z['peak_allocated_bytes'],gpu_peak_reserved_bytes=z['peak_reserved_bytes'])
 if (dest/'VALIDATED').exists():
  v.update(yaml.safe_load((dest/'cell_integration.yaml').read_text()));r['metric_state']='completed_validated'
  if r['architecture']=='gated': gates.append(yaml.safe_load((dest/'gate_summary.yaml').read_text()))
 elif not a.partial: raise RuntimeError('Missing validated metrics: '+r['run_id'])
 data.append(v)
f=pd.DataFrame(data); f['runtime_hours']=f.runtime_seconds/3600
for arch in ARCH:
 sel=f.architecture==arch; base=f.loc[sel & (f.latent_dim==50),'runtime_seconds'].iloc[0]
 f.loc[sel,'runtime_relative_dim50']=f.loc[sel,'runtime_seconds']/base
f['runtime_seconds_per_dimension']=f.runtime_seconds/f.latent_dim
ana=R/'analysis';fig=ana/'full_dimension_figures';fig.mkdir(exist_ok=True)
f.to_csv(ana/'full_dimension_comparison_metrics.csv',index=False)
f[['run_id','architecture','latent_dim','runtime_seconds','runtime_hours','runtime_relative_dim50','runtime_seconds_per_dimension','gpu_peak_allocated_bytes','gpu_peak_reserved_bytes']].to_csv(ana/'full_dimension_comparison_runtime.csv',index=False)
deltas=[]
for arch in ARCH:
 s=f[f.architecture==arch].set_index('latent_dim').reindex(DIMS)
 for i,d in enumerate(DIMS):
  for m in METRICS:
   deltas.append(dict(architecture=arch,latent_dim=d,metric=m,value=s.loc[d,m],delta_vs_dim50=s.loc[d,m]-s.loc[50,m],previous_dimension=DIMS[i-1] if i else np.nan,consecutive_delta=s.loc[d,m]-s.loc[DIMS[i-1],m] if i else np.nan))
pd.DataFrame(deltas).to_csv(ana/'full_dimension_comparison_deltas_vs_dim50.csv',index=False)
g=pd.DataFrame(gates,columns=['run_id','latent_dim','n','mean','median','sd','min','max','q05','q95','pct_lt_0.50','pct_lt_0.10']).sort_values('latent_dim')
g.to_csv(ana/'full_dimension_gated_gate_summary.csv',index=False)
summary=[]
for m,label in METRICS.items():
 t=f.pivot(index='latent_dim',columns='architecture',values=m).reindex(DIMS)
 for d in DIMS: summary.append(dict(metric=m,latent_dim=d,**t.loc[d].to_dict()))
pd.DataFrame(summary).to_csv(ana/'full_dimension_comparison_summary.csv',index=False)
save(rs)
def esc(s): return str(s).replace('_',r'\_').replace('%',r'\%')
def table(t,best=False,lower=False):
 lines=[r'\begin{center}\begin{tabular}{r'+'r'*len(t.columns)+'}',r'\toprule Dimension & '+' & '.join(esc(c).upper() for c in t.columns)+r'\\\midrule']
 for d,row in t.iterrows():
  optimum=row.min() if lower else row.max(); vals=[]
  for x in row:
   txt='--' if pd.isna(x) else f'{x:.4f}'
   if best and pd.notna(x) and x==optimum: txt=r'\textbf{'+txt+'}'
   vals.append(txt)
  lines.append(str(d)+' & '+' & '.join(vals)+r'\\')
 return '\n'.join(lines+[r'\bottomrule\end{tabular}\end{center}'])
def plot(m,label,log=False):
 plt.figure(figsize=(8,4))
 for arch in ARCH:
  s=f[f.architecture==arch].set_index('latent_dim').reindex(DIMS)
  plt.plot(range(len(DIMS)),s[m],marker='o',label=arch.upper())
 plt.xticks(range(len(DIMS)),DIMS,rotation=45);plt.xlabel('Latent dimension');plt.ylabel(label)
 if log: plt.yscale('log')
 plt.legend();plt.grid(alpha=.2);plt.tight_layout();name=m+('_log' if log else '')+'.pdf';plt.savefig(fig/name);plt.close();return name
def figure(name): return r'\begin{center}\includegraphics[width=.95\linewidth]{../analysis/full_dimension_figures/'+name+r'}\end{center}'
tex=[r'\documentclass{article}\usepackage[margin=0.7in]{geometry}\usepackage{booktabs,graphicx,longtable}\begin{document}',r'\title{Full SHARE-seq Ma-2020 capacity-response experiment}\author{}\date{}\maketitle',r'\section{Methods}',r'The comparison includes 32,231 paired cells in a fixed order, a fixed guidance graph, and latent dimensions 16, 32, 50, 64, 100, 128, 200, 256, 384, 512, 768, and 1024 for GCN, GAT, and GATED. The three dimension-50 models are reused. All configurations use model seed 0, hidden depth 2, hidden width 256, dropout 0.2, learning rate 0.002, graph loss weight 0.02, alignment loss weight 0.05, 10 negative samples, and cell batch size 128. The original pretraining, balancing and convergence procedures are retained. GAT uses negative slope 0.2; GATED uses gate initialization 0.95 and retention penalty 0. The canonical metric implementation uses the same cached 50-dimensional RNA and ATAC unimodal representations for every model dimension. FOSCTTM is lower-is-better; other integration metrics are higher-is-better. Gate summaries exclude fixed self-loops. Runtime is the time field of run\_info.yaml, separate from scheduler elapsed time.',r'\section{Results}']
complete=int(f.mean_average_precision.notna().sum());tex.append(f'Validated integration metrics are available for {complete} of 36 configurations. Missing results are shown as --. Smoke results are excluded.')
for m,label in METRICS.items():
 tex.extend([r'\subsection{'+label+'}',table(f.pivot(index='latent_dim',columns='architecture',values=m).reindex(index=DIMS,columns=ARCH),True,m=='foscttm'),figure(plot(m,label))])
tex.extend([r'\section{Computational cost}',table(f.pivot(index='latent_dim',columns='architecture',values='runtime_hours').reindex(index=DIMS,columns=ARCH),True,True),figure(plot('runtime_hours','Runtime (hours)')),figure(plot('runtime_hours','Runtime (hours)',True)),figure(plot('runtime_relative_dim50','Runtime relative to dim50'))])
tex.append(r'\section{Learned gates}')
for cols,label,name in [(['mean'],'Mean gate','gate_mean'),(['q05','median','q95'],'Gate quantiles','gate_quantiles'),(['pct_lt_0.50','pct_lt_0.10'],'Gates below threshold (%)','gate_thresholds')]:
 plt.figure(figsize=(8,4));z=g.set_index('latent_dim').reindex(DIMS)
 for c in cols: plt.plot(range(len(DIMS)),z[c],marker='o',label=c)
 plt.xticks(range(len(DIMS)),DIMS,rotation=45);plt.xlabel('Latent dimension');plt.ylabel(label);plt.legend();plt.grid(alpha=.2);plt.tight_layout();plt.savefig(fig/(name+'.pdf'));plt.close();tex.append(figure(name+'.pdf'))
tex.append(r'\section{Capacity response and limitations}')
if complete<36:
 tex.append('The capacity response cannot yet be determined from the incomplete sweep. In particular, the sufficiency of dimension 50, gains at 100--256, saturation beyond 256, and degradation at 512--1024 remain unresolved.')
else:
 for arch in ARCH:
  s=f[f.architecture==arch].set_index('latent_dim');tex.append(r'\subsection{'+arch.upper()+'}')
  for lo,hi,label in [(16,64,'Low capacity'),(100,256,'Standard capacity'),(384,512,'High capacity'),(768,1024,'Very high capacity')]:
   changes=[f"{METRICS[m]} {s.loc[hi,m]-s.loc[lo,m]:+.4f}" for m in METRICS]
   tex.append(f'{label} ({lo}--{hi}), endpoint changes: '+', '.join(changes)+'.')
  for d in [256,512,1024]:
   tex.append(f'Dimension {d} relative to 50: '+', '.join(f'{METRICS[m]} {s.loc[d,m]-s.loc[50,m]:+.4f}' for m in METRICS)+f'; runtime ratio {s.loc[d,"runtime_relative_dim50"]:.2f}.')
 tex.append('These changes quantify the observed gains and tradeoffs; no universal minimum meaningful effect was prespecified. A plateau should be judged across metrics using the consecutive-change table, rather than by a single maximum score. Deterioration in integration metrics alone does not establish overfitting without independent validation.')
tex.append('This is a descriptive capacity-response experiment with one model seed per configuration. No significance tests or statistically optimal dimension are claimed. Variation across dimensions cannot estimate seed uncertainty or prove instability. Feature consistency is unavailable because no applicable independent reference evaluation is available. Comparisons with the earlier PBMC experiment share the dimension-sweep design and metric implementation but involve different datasets and cell counts. Dimensions 1536 and 2048 require review of the completed 768-to-1024 response and are not automatically submitted.')
tex.append(r'\end{document}')
report=R/'reports/full_dimension_comparison.tex';report.write_text('\n\n'.join(tex)+'\n')
subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error',report.name],cwd=report.parent,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
print(f'Created report: {complete}/36 metric configurations available')
