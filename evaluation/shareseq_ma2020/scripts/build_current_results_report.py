#!/usr/bin/env python
"""Build a read-only scientific snapshot; write only reports/current artifacts.

No model loading, training, scheduler calls, or integration-metric computation.
"""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
os.environ.setdefault('MPLCONFIGDIR', '/tmp/shareseq_current_matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports'
FIG = REPORT / 'figures_current'
FIG.mkdir(parents=True, exist_ok=True)
STAMP = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
METRICS = ['mean_average_precision', 'normalized_mutual_info', 'avg_silhouette_width',
           'avg_silhouette_width_batch', 'graph_connectivity', 'foscttm',
           'neighbor_conservation', 'seurat_alignment_score']
SHORT = ['MAP', 'NMI', 'ASW', 'Batch ASW', 'Graph conn.', 'FOSCTTM', 'Neighbor cons.', 'Seurat align.']
LABEL = dict(zip(METRICS, SHORT))
GATES = ['mean', 'median', 'min', 'max', 'pct_lt_0.50', 'pct_lt_0.10']
GLABEL = ['Mean', 'Median', 'Minimum', 'Maximum', r'\% below 0.50', r'\% below 0.10']
ARCH = ['gcn', 'gat', 'gated']
SIZES = [8000, 16000, 24000, 32231]
manifest_names = ['master_experiment_manifest.csv', 'matched_subsample_manifest.csv', 'architecture_by_size_manifest.csv']
manifest_rows = {n: list(csv.DictReader((ROOT/'manifests'/n).open())) for n in manifest_names}
assert [len(manifest_rows[n]) for n in manifest_names] == [26,18,30]
configs = {}
for name, rows in manifest_rows.items():
    for r in rows:
        if r['run_id'] in configs:
            for key in ['architecture','cell_count','model_seed','subsample_seed','gate_init','output_directory','cell_manifest_path']:
                assert configs[r['run_id']][key] == r[key], (r['run_id'],key)
        else:
            configs[r['run_id']] = r
assert len(configs) == 44
assert len({r['graph_checksum'] for r in configs.values()}) == 1
for path in {r['graph_path'] for r in configs.values()}:
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == next(iter(configs.values()))['graph_checksum']
# Freeze completion eligibility before doing any lengthy validation.
required = ['final.dill','rna_latent.csv','atac_latent.csv','feature_latent.csv','run_info.yaml','requested_configuration.json']
snapshot = {rid: {f: (Path(r['output_directory'])/f).is_file() and (Path(r['output_directory'])/f).stat().st_size > 0
                   for f in required+['cell_integration.yaml','gate_summary.yaml','gates.csv','unirep_inputs.json']}
            for rid,r in configs.items()}
source_hashes = {}
def source(p):
    p = Path(p)
    rel = 'evaluation/shareseq_ma2020/' + str(p.relative_to(ROOT))
    if p.is_file() and p.stat().st_size < 2_000_000:
        source_hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return rel

def validate_training(r):
    out = Path(r['output_directory']); rid=r['run_id']
    assert all(snapshot[rid][f] for f in required), 'Training artifacts incomplete at snapshot'
    stamp=json.loads((out/'requested_configuration.json').read_text())
    for key in ['run_id','architecture','cell_count','replicate_source','subsample_seed','model_seed','latent_dim','gate_init','lam_keep','gat_negative_slope','graph_checksum','git_commit']:
        assert str(stamp[key])==str(r[key]), 'Configuration mismatch: '+key
    ids=Path(r['cell_manifest_path']).read_text().splitlines()
    assert len(ids)==int(r['cell_count']) and len(set(ids))==len(ids)
    for mod in ['rna','atac']:
        a=pd.read_csv(out/f'{mod}_latent.csv', header=None,index_col=0)
        assert a.index.tolist()==ids and a.shape==(len(ids),int(r['latent_dim']))
        assert np.isfinite(a.values).all()
    feature_ids=set()
    for chunk in pd.read_csv(out/'feature_latent.csv',header=None,index_col=0,chunksize=50000):
        assert chunk.shape[1]==int(r['latent_dim']) and np.isfinite(chunk.values).all()
        assert chunk.index.is_unique and not (feature_ids & set(chunk.index))
        feature_ids.update(chunk.index)
    assert feature_ids
    info=yaml.unsafe_load((out/'run_info.yaml').read_text())
    runtime=float(info['time']);assert np.isfinite(runtime) and runtime>0
    expected={'gcn':'GLUE','gat':'GLUE_GAT','gated':'GLUE_GATED'}[r['architecture']]
    assert f'/{expected}/evaluation/workflow/scripts/run_GLUE.py' in info['cmd']
    if r['architecture']=='gat' and r['cell_label']!='full':
        # An exact correct import in a recovery log plus completed matching artifacts
        # excludes incomplete pre-recovery configurations.
        logs=list((ROOT/'logs').glob('matched_train_58973921_*.out'))
        assert any(rid in p.read_text() and 'scglue.__file__=/project/6001426/paa40/GlUE_Exp/GLUE_GAT/scglue/__init__.py' in p.read_text() for p in logs), 'No validated recovery provenance'
    return runtime

def validate_gates(out, rid):
    assert snapshot[rid]['gate_summary.yaml'] and snapshot[rid]['gates.csv']
    summary=yaml.safe_load((out/'gate_summary.yaml').read_text());assert summary['run_id']==rid
    g=pd.read_csv(out/'gates.csv')
    assert not g.duplicated(['source','target']).any()
    loops=g.is_self_loop.astype(str).str.lower().eq('true')
    assert np.isfinite(g.gate).all() and g.gate.between(0,1).all()
    assert (g.loc[loops,'gate']==1).all() and g.loc[loops,'logit'].isna().all()
    x=g.loc[~loops,'gate']; logits=g.loc[~loops,'logit']
    assert np.isfinite(logits).all() and np.allclose(x,1/(1+np.exp(-logits)),rtol=1e-6,atol=1e-7)
    check={'n':len(x),'mean':x.mean(),'median':x.median(),'sd':x.std(ddof=1),'min':x.min(),'max':x.max(),'q05':x.quantile(.05),'q95':x.quantile(.95),'pct_lt_0.50':100*(x<.5).mean(),'pct_lt_0.10':100*(x<.1).mean()}
    for k,v in check.items():assert np.isfinite(summary[k]) and np.isclose(v,summary[k],rtol=2e-6,atol=2e-7), (rid,k,v,summary[k])
    return summary

audit=[];records=[]; gates=[]
for rid,r in configs.items():
    out=Path(r['output_directory']); a={'run_id':rid,'training_valid':False,'metrics_valid':False,'gates_valid':False,'reasons':[]}
    try:
        runtime=validate_training(r); a['training_valid']=True
    except Exception as e:
        a['reasons'].append(str(e));audit.append(a);continue
    rec={**r,'cell_count':int(r['cell_count']),'runtime':runtime}
    try:
        assert snapshot[rid]['cell_integration.yaml'], 'Integration metrics unavailable at snapshot'
        m=yaml.safe_load((out/'cell_integration.yaml').read_text())
        assert set(METRICS).issubset(m) and all(np.isfinite(float(m[k])) for k in METRICS)
        assert snapshot[rid]['unirep_inputs.json'], 'Missing metric input provenance'
        unirep=json.loads((out/'unirep_inputs.json').read_text())
        assert set(unirep)=={'rna','atac'} and all(Path(p).is_file() for p in unirep.values())
        rec.update({k:float(m[k]) for k in METRICS});a['metrics_valid']=True
        if 'feature_consistency' in m and np.isfinite(m['feature_consistency']):rec['feature_consistency']=m['feature_consistency']
    except Exception as e:a['reasons'].append(str(e))
    if r['architecture']=='gated':
        try:
            g=validate_gates(out,rid);gates.append({**rec,**{'gate_'+k:g[k] for k in GATES}});a['gates_valid']=True
        except Exception as e:a['reasons'].append('Gate validation: '+str(e))
    records.append(rec);audit.append(a)
    for f in ['requested_configuration.json','run_info.yaml','cell_integration.yaml','gate_summary.yaml','unirep_inputs.json']:
        source(out/f)
    print(rid, a['training_valid'], a['metrics_valid'], a['gates_valid'],flush=True)
D=pd.DataFrame(records);A=pd.DataFrame(audit);G=pd.DataFrame(gates)
valid_metrics=set(A.loc[A.metrics_valid,'run_id']);M=D[D.run_id.isin(valid_metrics)].copy()
size_ids={r['run_id'] for r in manifest_rows['architecture_by_size_manifest.csv']}
S=D[D.run_id.isin(size_ids)];SM=M[M.run_id.isin(size_ids)];SG=G[G.run_id.isin(size_ids)]
F=SM[SM.cell_count==32231].set_index('architecture').loc[ARCH].reset_index()
assert len(F)==3
assert len({(Path(p)/'unirep_inputs.json').read_text() for p in F.output_directory})==1
I=M[(M.architecture=='gated')&(M.cell_count==32231)].copy()
IG=G[(G.architecture=='gated')&(G.cell_count==32231)].copy()
assert not I.duplicated(['gate_init','model_seed']).any()
assert set(I.gate_init)<=set(['0.5','0.50','0.7','0.70','0.9','0.90','0.95','0.99'])
for _,grp in I.groupby('gate_init'):assert set(grp.model_seed)<=set(['0','1','2'])
for _,grp in SM[SM.cell_count<32231].groupby(['architecture','cell_count']):
    assert set(grp.subsample_seed)<=set(['0','1','2']) and not grp.subsample_seed.duplicated().any() and set(grp.model_seed)=={'0'}
for _,grp in S[S.cell_count<32231].groupby(['cell_count','subsample_seed']):assert grp.cell_manifest_path.nunique()==1
assert len({Path(p).read_bytes() for p in I.cell_manifest_path})==1

# Descriptive, inexpensive rank summaries of existing finite scalar outputs.
assoc=[]
for gk in GATES:
    for mk in METRICS:
        z=IG[['gate_'+gk,mk]].dropna()
        rho=float(spearmanr(z.iloc[:,0],z.iloc[:,1])[0]) if len(z)>=3 and z.iloc[:,0].nunique()>1 and z.iloc[:,1].nunique()>1 else None
        assoc.append({'gate_statistic':gk,'metric':mk,'spearman_rho':rho,'n_runs':len(z)})
C=pd.DataFrame(assoc)
D.to_csv(REPORT/'current_valid_runs.csv',index=False)
G.to_csv(REPORT/'current_valid_gate_summaries.csv',index=False)
C.to_csv(REPORT/'current_gate_performance_associations.csv',index=False)

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':220})
colors={'gcn':'#4477AA','gat':'#CC6677','gated':'#228833'}
def save(name):
    plt.savefig(FIG/(name+'.pdf'),bbox_inches='tight');plt.savefig(FIG/(name+'.png'),bbox_inches='tight');plt.close()
fig,axes=plt.subplots(2,4,figsize=(12,5.6))
for ax,k in zip(axes.flat,METRICS):
    ax.bar([a.upper() for a in ARCH],F[k],color=[colors[a] for a in ARCH]);ax.set_title(LABEL[k]+(' ↓' if k=='foscttm' else ' ↑'));ax.tick_params(axis='x',labelsize=9)
fig.suptitle('Full SHARE-seq: 32,231 paired cells; one primary run per architecture');fig.tight_layout();save('full_architecture_metrics')
fig,ax=plt.subplots(figsize=(6,3.4));ax.bar([a.upper() for a in ARCH],F.runtime/3600,color=[colors[a] for a in ARCH]);ax.set_ylabel('Canonical training runtime (hours)')
for j,x in enumerate(F.runtime/3600):ax.text(j,x,f'{x:.2f} h',ha='center',va='bottom')
ax.set_ylim(0,max(F.runtime/3600)*1.15);save('full_runtime')
fig,axes=plt.subplots(2,4,figsize=(12,5.6))
for ax,k in zip(axes.flat,METRICS):
    z=SM[SM.architecture=='gated'].groupby('cell_count')[k].agg(['mean','std']);ax.errorbar(z.index,z['mean'],yerr=z['std'].fillna(0),marker='o',color=colors['gated']);ax.set_title(LABEL[k]);ax.set_xticks(SIZES);ax.set_xticklabels(['8k','16k','24k','Full'])
fig.suptitle('GATED by paired-cell count; mean ± sample SD (full: one reference)');fig.tight_layout();save('gated_size_metrics')
fig,axes=plt.subplots(1,2,figsize=(10,3.6))
for ax,key in zip(axes,['gate_mean','gate_pct_lt_0.50']):
    z=SG.groupby('cell_count')[key].agg(['mean','std']);ax.errorbar(z.index,z['mean'],yerr=z['std'].fillna(0),marker='o',color=colors['gated']);ax.set_xticks(SIZES);ax.set_xticklabels(['8k','16k','24k','Full']);ax.set_ylabel('Mean learned gate' if key=='gate_mean' else 'Non-self edges below 0.50 (%)')
fig.tight_layout();save('gated_size_gates')
fig,axes=plt.subplots(2,4,figsize=(12,5.6))
for ax,k in zip(axes.flat,METRICS):
    z=I.groupby('gate_init')[k].agg(['mean','std']);ax.errorbar(np.arange(len(z)),z['mean'],yerr=z['std'].fillna(0),marker='o');ax.set_xticks(np.arange(len(z)));ax.set_xticklabels([f'{float(x):.2f}' for x in z.index]);ax.set_title(LABEL[k])
fig.suptitle('Full-data gate initialization: mean ± sample SD across model seeds');fig.tight_layout();save('gate_init_metrics')
fig,axes=plt.subplots(1,2,figsize=(10,3.6))
for ax,key in zip(axes,['gate_mean','gate_pct_lt_0.50']):
    z=IG.groupby('gate_init')[key].agg(['mean','std']);ax.errorbar(np.arange(len(z)),z['mean'],yerr=z['std'].fillna(0),marker='o');ax.set_xticks(np.arange(len(z)));ax.set_xticklabels([f'{float(x):.2f}' for x in z.index]);ax.set_xlabel('Gate initialization');ax.set_ylabel('Mean learned gate' if key=='gate_mean' else 'Non-self edges below 0.50 (%)')
fig.tight_layout();save('gate_init_gates')
fig,ax=plt.subplots(figsize=(7,4))
for arch,g in S.groupby('architecture'):
    z=g.groupby('cell_count').runtime.agg(['mean','std']);ax.errorbar(z.index,z['mean']/3600,yerr=z['std'].fillna(0)/3600,marker='o',label=arch.upper(),color=colors[arch])
ax.set_xticks(SIZES);ax.set_xticklabels(['8,000','16,000','24,000','32,231']);ax.set_xlabel('Paired cells');ax.set_ylabel('Canonical training runtime (hours)');ax.legend();fig.tight_layout();save('runtime_scaling')

def esc(x):
    return str(x).replace('\\',r'\textbackslash{}').replace('_',r'\_').replace('%',r'\%').replace('&',r'\&').replace('#',r'\#')
def fmt(x):return '--' if x is None or not np.isfinite(x) else f'{x:.4f}'
def agg(g,k,scale=1):
    if k not in g:return '--'
    x=pd.to_numeric(g[k],errors='coerce').dropna()/scale
    if not len(x):return '--'
    return fmt(x.iloc[0]) if len(x)==1 else fmt(x.mean())+r' $\pm$ '+fmt(x.std(ddof=1))
T=[r'''\documentclass[10pt]{article}
\usepackage[margin=0.65in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{booktabs,longtable,graphicx,array,amsmath}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\begin{document}
\title{SHARE-seq Ma-2020: Currently Available Results}
\author{}
\date{Snapshot: '''+esc(STAMP)+r'''}
\maketitle
''']
def para(x):T.append(x+'\n')
def section(x):T.append(r'\section{'+x+'}')
def sources(g,files):
    for _,r in g.iterrows():
        for f in files:
            p=Path(r.output_directory)/f
            if p.is_file():T.append('% Source: '+source(p))
def table(title,heads,rows,g=None,files=('cell_integration.yaml','run_info.yaml')):
    if g is not None:sources(g,files)
    T.append(r'\begin{center}\begin{minipage}{\textwidth}\centering\textbf{'+title+r'}\par\smallskip')
    T.append(r'\resizebox{\textwidth}{!}{\begin{tabular}{l'+('r'*(len(heads)-1))+r'}\toprule')
    T.append(' & '.join(heads)+r' \\\midrule')
    T.extend(' & '.join(map(str,row))+r' \\' for row in rows)
    T.append(r'\bottomrule\end{tabular}}\end{minipage}\end{center}')
def fig(name,caption):
    T.append(r'\begin{center}\includegraphics[width=0.96\textwidth]{figures_current/'+name+r'.pdf}\par\small '+caption+r'\end{center}')
def metric_tables(title,groups,g):
    for keys in [METRICS[:4],METRICS[4:]]:
        table(title,['Configuration','n']+[LABEL[k]+(r' $\downarrow$' if k=='foscttm' else r' $\uparrow$') for k in keys],[[label,str(len(grp))]+[agg(grp,k) for k in keys] for label,grp in groups],g)
section('Current experiment status')
para(f'This snapshot validates {len(D)} completed training configurations, {len(M)} configurations with integration metrics, and {len(G)} configurations with learned-gate summaries. The manifests define 44 distinct configurations: 26 original experiments and 18 matched GCN/GAT subsample configurations. Reused reference runs are counted once in this total. Availability was frozen at report start; no running task was awaited and no missing metric was computed.')
para('Validation checks completed-artifact presence, configuration stamps, finite paired RNA/ATAC and feature embeddings, exact cell-manifest ordering, finite canonical metrics and runtime, and recorded metric-input paths. Gate summaries are checked against existing edge CSVs, excluding fixed self-loops. Model checkpoints are checked for presence and nonzero size; models are not deserialized. Missing results are shown as --.')
section('Full-data GCN vs GAT vs GATED')
para('The primary comparison uses 32,231 paired cells, latent dimension 50 and model seed 0. GATED uses gate initialization 0.95. These are single runs per architecture, so no replicate uncertainty or significance is implied.')
rows=[]
for _,r in F.iterrows():
    vals=[]
    for k in METRICS:
        x=fmt(r[k]);best=F[k].min() if k=='foscttm' else F[k].max()
        if len(F[k].dropna())==3 and r[k]==best:x=r'\textbf{'+x+'}'
        vals.append(x)
    rows.append([r.architecture.upper()]+vals+[f'{r.runtime/60:.2f}',f'{r.runtime/3600:.3f}'])
table('Primary full-data architecture comparison',['Architecture']+[LABEL[k]+(r' $\downarrow$' if k=='foscttm' else r' $\uparrow$') for k in METRICS]+['Runtime (min)','Runtime (h)'],rows,F)
para('Arrows specify preferred integration-metric directions; lower FOSCTTM is better and all other displayed integration scores are higher-is-better. Bold indicates the best comparable score among all three architectures. Runtime is a computational cost, not an integration-quality score.')
para(r'\begingroup\raggedright\small Exact pipeline metric names: '+', '.join(r'\texttt{'+esc(k)+'}' for k in METRICS)+'. Neighbor consistency here means the pipeline metric '+r'\texttt{neighbor\_conservation}'+'. Feature consistency is not present in the validated canonical integration outputs and is omitted; it was not computed for this snapshot.'+r'\par\endgroup')
gatsec=float(F.loc[F.architecture=='gat','runtime'].iloc[0])
para(f'Runtime uses the canonical experiment field \\texttt{{time}} in each \\texttt{{run\\_info.yaml}}, in seconds. Full GAT records {gatsec:.2f} seconds ({gatsec/60:.2f} minutes; {gatsec/3600:.3f} hours), approximately 7 h 53 min 21 s. The separately recorded scheduler elapsed time of 7:59:44 includes job overhead and is not used in the numerical runtime tables.')
fig('full_architecture_metrics','Independent metric panels; bars start at zero. These single-run comparisons do not estimate uncertainty.')
section('Architecture comparison across available subsamples')
T.append('% Source: evaluation/shareseq_ma2020/manifests/architecture_by_size_manifest.csv')
av=[]
for size in SIZES:
    av.append([f'{size:,}']+[str(len(SM[(SM.cell_count==size)&(SM.architecture==a)])) for a in ARCH]+[str(len(S[(S.cell_count==size)&(S.architecture==a)])) for a in ARCH])
table('Availability: valid metrics and completed training',['Cells','GCN metric n','GAT metric n','GATED metric n','GCN train n','GAT train n','GATED train n'],av,S)
para('Metric n counts completed training with validated metrics; train n also includes completed models whose metrics are unavailable. Zero in this availability table is a count, never an imputed metric. For subsamples, replication is cell-selection seeds 0, 1, 2 at fixed model seed 0. Aggregates with n=3 are mean $\\pm$ sample SD (ddof=1); n=1 is a single value. Full-data rows reuse the designated primary references.')
groups=[(f'{size:,} / {arch.upper()}',SM[(SM.cell_count==size)&(SM.architecture==arch)]) for size in SIZES[:-1] for arch in ARCH]
metric_tables('Available matched-subsample integration metrics',groups,SM[SM.cell_count<32231])
section('GATED sample-size behavior')
groups=[(f'{size:,}',SM[(SM.cell_count==size)&(SM.architecture=='gated')]) for size in SIZES]
metric_tables('GATED integration metrics by cell count',groups,SM[SM.architecture=='gated'])
para('All subsample runs use gate initialization 0.95 and model seed 0. Full data use only the canonical 0.95/model-seed-0 reference; its reuse here does not add an independent replicate. Runtime for these runs appears in the runtime section.')
fig('gated_size_metrics','Error bars summarize subsample-seed variation; the full reference has no estimated SD.')
section('Full-data gate-initialization sensitivity')
para('All initializations use the same 32,231 paired cells. Replication here is model seeds 0, 1, 2, not subsample seeds. Reported SDs describe model-initialization variability. The 0.95/model-seed-0 configuration is the same canonical reference used above.')
groups=[(f'{float(init):.2f}',g) for init,g in I.groupby('gate_init')]
metric_tables('Performance by gate initialization',groups,I)
table('Runtime by gate initialization',['Gate init','n','Minutes','Hours'],[[label,len(g),agg(g,'runtime',60),agg(g,'runtime',3600)] for label,g in groups],I,('run_info.yaml',))
fig('gate_init_metrics','Mean and sample SD across available model seeds; directions follow the full-data metric table.')
section('Learned-gate distributions')
para('All gate statistics exclude fixed self-loops. The table entries aggregate run-level statistics, not pooled edges. Thus the minimum and maximum columns are the mean and SD of each run\'s minimum and maximum when replicated; percentages use a 0--100 scale.')
table('GATED gate summaries by cell count',['Cells','n']+GLABEL,[[f'{size:,}',len(g)]+[agg(g,'gate_'+k) for k in GATES] for size in SIZES for g in [SG[SG.cell_count==size]]],SG,('gate_summary.yaml','gates.csv'))
table('Full-data gate summaries by initialization',['Gate init','n']+GLABEL,[[f'{float(init):.2f}',len(g)]+[agg(g,'gate_'+k) for k in GATES] for init,g in IG.groupby('gate_init')],IG,('gate_summary.yaml','gates.csv'))
fig('gated_size_gates','Available learned-gate summaries by paired-cell count; mean and sample SD across runs.')
fig('gate_init_gates','Final learned-gate summaries by initialization; mean and sample SD across model seeds.')
section('Gate-performance relationship')
para('Scientific question: Do substantially different learned gate distributions correspond to substantially different integration performance on SHARE-seq? The following Spearman correlations are descriptive run-level summaries across full-data GATED runs. They pool initializations and seeds, do not establish causality, and are not significance tests. A -- coefficient means a constant variable or insufficient observations.')
T.append('% Source: evaluation/shareseq_ma2020/reports/current_gate_performance_associations.csv; derived from the canonical files listed below.')
table('Descriptive Spearman correlations',['Gate statistic','n']+[LABEL[k] for k in METRICS],[[esc(gk),str(int(C[C.gate_statistic==gk].n_runs.iloc[0]))]+[fmt(C[(C.gate_statistic==gk)&(C.metric==mk)].spearman_rho.iloc[0]) for mk in METRICS] for gk in GATES],IG,('gate_summary.yaml','cell_integration.yaml'))
means=I.groupby('gate_init')[METRICS].mean();gate_means=IG.groupby('gate_init').gate_mean.mean()
para(f'Mean learned gate (averaged across seeds within initialization) ranges from {gate_means.min():.4f} to {gate_means.max():.4f}. The table below shows the observed range of initialization-level mean integration scores. These ranges describe magnitude without imposing a threshold for biological or practical importance.')
table('Range of initialization-level mean performance',['Metric','Lowest mean','Highest mean','Range'],[[esc(k),fmt(means[k].min()),fmt(means[k].max()),fmt(means[k].max()-means[k].min())] for k in METRICS],I,('cell_integration.yaml',))
section('Runtime comparison')
table('Canonical training runtime across available sizes',['Cells','Architecture','n','Minutes','Hours'],[[f'{size:,}',arch.upper(),len(g),agg(g,'runtime',60),agg(g,'runtime',3600)] for size in SIZES for arch in ARCH for g in [S[(S.cell_count==size)&(S.architecture==arch)]]],S,('run_info.yaml',))
para('Runtime can be reported for validated completed training even when integration metrics are absent. Subsample SDs use cell-selection seeds; each full-data entry is a single primary run. Comparisons describe these recorded experiments and do not isolate hardware, convergence length, or algorithmic causes.')
fig('full_runtime','Full-data primary runs; canonical experiment runtime.')
fig('runtime_scaling','Completed size-comparison runs only; missing configurations are omitted. Error bars are sample SD where replicated.')
section('Current conclusions')
ratio_gcn=gatsec/float(F.loc[F.architecture=='gcn','runtime'].iloc[0]);ratio_gated=gatsec/float(F.loc[F.architecture=='gated','runtime'].iloc[0])
para(f'Full-data GAT takes {ratio_gcn:.2f} times the canonical runtime of GCN and {ratio_gated:.2f} times that of GATED in these runs. Its computational cost is therefore substantially higher in this experiment.')
winners={a:[] for a in ARCH}
for k in METRICS:winners[F.loc[F[k].idxmin() if k=='foscttm' else F[k].idxmax(),'architecture']].append(LABEL[k])
para('The single-run full-data metrics show tradeoffs: '+'; '.join(a.upper()+' has the best '+', '.join(v) for a,v in winners.items() if v)+'. No architecture is uniformly best, and single primary runs do not establish statistical superiority.')
para(f'Learned gate distributions vary with initialization (mean-gate range {gate_means.min():.4f}--{gate_means.max():.4f}); integration-score changes are metric dependent, as quantified above. The descriptive associations do not establish that changing a gate distribution causes a change in integration quality. Three replicates per setting support descriptive variability estimates rather than strong significance claims.')
section('Results still pending')
missing=[]
for size in SIZES[:-1]:
    for arch in ARCH:
        g=SM[(SM.cell_count==size)&(SM.architecture==arch)]
        absent=sorted(set(['0','1','2'])-set(g.subsample_seed))
        if absent:missing.append(f'{size:,} {arch.upper()}: missing validated metrics for subsample seeds '+', '.join(absent))
para('Matched GAT subsample results are incomplete and are therefore excluded from the corresponding comparison.' if any('GAT:' in x for x in missing) else 'All matched GAT subsample metrics were available at the snapshot.')
for x in missing:para(esc(x)+'.')
para('Completed GCN subsample models without metrics contribute only to training availability and runtime. Feature consistency is unavailable in the validated metric files. No values were inferred from training logs or filled in for missing results.')
T.append(r'\end{document}')
(REPORT/'shareseq_results_current.tex').write_text('\n'.join(T)+'\n')
summary={'snapshot_utc':STAMP,'manifest_row_counts':{k:len(v) for k,v in manifest_rows.items()},'unique_configurations':len(configs),'training_valid':len(D),'metrics_valid':len(M),'gates_valid':len(G),'full_metrics':METRICS,'availability':av,'missing':missing,'runs':audit,'source_sha256':source_hashes,'full_runtime_gat_over_gcn':ratio_gcn,'full_runtime_gat_over_gated':ratio_gated,'gate_initialization_mean_gate_range':[float(gate_means.min()),float(gate_means.max())]}
(REPORT/'current_results_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['runs','source_sha256']},indent=2))
