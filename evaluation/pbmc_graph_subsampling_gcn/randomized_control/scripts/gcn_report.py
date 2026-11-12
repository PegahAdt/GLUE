"""Six-condition original GCN report and matched completed GATED comparisons."""
import json
from pathlib import Path
import shutil
import subprocess
import textwrap
import numpy as np
import pandas as pd
from common import BASE, EXPERIMENT, GATED, CONDITIONS, SHARED, sha, save_json
import reporting as shared


def require_design(frame):
    pairs=set(zip(frame.condition,frame.model_seed))
    if len(frame)!=18 or pairs!={(c,s) for c in CONDITIONS for s in range(3)} or set(frame.graph_seed)!={0}:
        raise ValueError('Full report requires exactly six conditions x seeds 0,1,2, graph seed 0')


def compare_models(gcn, gated):
    require_design(gcn); require_design(gated)
    if any(c.startswith('gate_') for c in gcn): raise ValueError('Gate metrics forbidden for GCN')
    keys=['condition','model_seed','graph_seed']
    names=[m for m in shared.PERFORMANCE if m in gcn and m in gated and not m.startswith('gate_')]
    aligned=gcn[keys+names].merge(gated[keys+names],on=keys,suffixes=('_gcn','_gated'),validate='one_to_one')
    per_seed=[]; summary=[]
    for metric in names:
        for condition,g in aligned.groupby('condition',sort=False):
            a=pd.to_numeric(g[metric+'_gcn'],errors='coerce')
            b=pd.to_numeric(g[metric+'_gated'],errors='coerce')
            diff=a-b
            for index,row in g.iterrows():
                per_seed.append(dict(condition=condition,model_seed=int(row.model_seed),graph_seed=0,metric=metric,
                    gcn=row[metric+'_gcn'],gated=row[metric+'_gated'],gcn_minus_gated=diff.loc[index]))
            summary.append(dict(condition=condition,metric=metric,gcn_n=int(a.count()),gcn_mean=a.mean(),gcn_sd=a.std(ddof=1),
                gated_n=int(b.count()),gated_mean=b.mean(),gated_sd=b.std(ddof=1),
                seed_matched_difference_mean=diff.mean(),seed_matched_difference_sd=diff.std(ddof=1),
                higher_better=shared.PERFORMANCE[metric][1]))
    return pd.DataFrame(per_seed),pd.DataFrame(summary)


def comparison_figures(output, frame, gated):
    import matplotlib.pyplot as plt
    metrics=['foscttm','matching_recall_at_1','matching_recall_at_5','matching_recall_at_10',
             'avg_silhouette_width','label_transfer_rna_to_atac_macro_f1']
    files=[]
    def save(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf']: fig.savefig(output/'figures'/(name+'.'+ext),bbox_inches='tight',dpi=350)
        plt.close(fig); files.append(name)
    for name,conditions in [('gcn_vs_gated_all_conditions',CONDITIONS),('gcn_vs_gated_original_randomized',['original','randomized'])]:
        fig,axes=plt.subplots(2,3,figsize=(14,8))
        for ax,m in zip(axes.flat,metrics):
            for model,data,offset,color in [('GCN',frame,-.18,'#407a9c'),('GATED',gated,.18,'#c07838')]:
                group=data.groupby('condition')[m]
                means=group.mean().reindex(conditions);sd=group.std(ddof=1).reindex(conditions)
                x=np.arange(len(conditions))+offset
                ax.bar(x,means,width=.34,label=model,color=color,alpha=.65)
                ax.errorbar(x,means,yerr=sd,fmt='none',color='black',capsize=3)
                for i,c in enumerate(conditions):
                    vals=data.loc[data.condition==c,m].to_numpy()
                    ax.scatter(i+offset+np.linspace(-.06,.06,len(vals)),vals,s=12,color=color,zorder=3)
            ax.set_xticks(np.arange(len(conditions))); ax.set_xticklabels(conditions,rotation=35,ha='right')
            ax.set_ylabel(shared.PERFORMANCE[m][0])
        axes.flat[0].legend();fig.suptitle('GCN versus GATED: dots = model seeds; bars = mean; error bars = sample SD')
        save(fig,name)
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    for ax,m in zip(axes.flat,metrics):
        for label,data,color in [('GCN',frame,'#407a9c'),('GATED',gated,'#c07838')]:
            retained=data[data.condition!='randomized']
            for seed,g in retained.groupby('model_seed'):
                g=g.sort_values('edge_count_fraction');ax.plot(100*g.edge_count_fraction,g[m],color=color,alpha=.2)
            grouped=retained.groupby('edge_count_fraction')[m]
            ax.errorbar(100*grouped.mean().index,grouped.mean(),yerr=grouped.std(ddof=1),fmt='o-',capsize=3,color=color,label=label)
        ax.set_xlabel('Biological relations retained (%)'); ax.set_ylabel(shared.PERFORMANCE[m][0])
    axes.flat[0].legend(); fig.suptitle('Graph subsampling sensitivity; randomized control excluded')
    save(fig,'gcn_vs_gated_retention_sensitivity')
    return files


def generate(output):
    output=Path(output)
    frame=pd.read_csv(output/'per_run_metrics.csv',na_values=['N/A'])
    summary=pd.read_csv(output/'summary_metrics.csv',na_values=['N/A'])
    baseline=pd.read_csv(output/'baseline_comparison.csv',na_values=['N/A'])
    config=json.loads((output/'evaluation_config.json').read_text())
    smoke=config['evaluation_mode']=='smoke'
    if not smoke: require_design(frame)
    if any(c.startswith('gate_') for c in frame): raise ValueError('GCN report contains gate metrics')
    plots=shared.figures(output,frame,summary,order=CONDITIONS)
    tables=[];ranks=[]
    for metric,(label,higher) in shared.PERFORMANCE.items():
        part=summary[summary.metric==metric].set_index('condition')
        if part.empty: continue
        entry={'Metric':label}
        for c in CONDITIONS:
            entry[c]=shared.mean_sd(part.loc[c,'mean'],part.loc[c,'sd'],part.loc[c,'n']) if c in part.index else 'N/A'
        tables.append(entry)
        rank=part.reset_index();rank['rank']=rank['mean'].rank(ascending=not higher,method='min');ranks.append(rank)
    pd.concat(ranks,ignore_index=True).to_csv(output/'condition_rankings.csv',index=False,na_rep='N/A')
    contrasts=baseline[baseline.condition=='randomized']
    contrasts.to_csv(output/'original_vs_randomized.csv',index=False,na_rep='N/A')
    model_table='No full-model comparison is interpreted from the smoke test.'
    if not smoke:
        gated=pd.read_csv(GATED/'reports/full/per_run_metrics.csv',na_values=['N/A'])
        per_seed,comparison=compare_models(frame,gated)
        per_seed.to_csv(output/'gcn_vs_gated_per_seed.csv',index=False,na_rep='N/A')
        comparison.to_csv(output/'gcn_vs_gated_summary.csv',index=False,na_rep='N/A')
        pd.concat([frame.assign(architecture='GCN'),gated[[c for c in gated if not c.startswith('gate_')]].assign(architecture='GATED')],ignore_index=True).to_csv(output/'combined_per_seed_metrics.csv',index=False,na_rep='N/A')
        selected=comparison[comparison.metric.isin(['foscttm','matching_recall_at_1','avg_silhouette_width','avg_silhouette_width_batch','label_transfer_rna_to_atac_macro_f1'])].copy()
        selected['GCN mean ± SD']=selected.apply(lambda r:shared.mean_sd(r.gcn_mean,r.gcn_sd,r.gcn_n),axis=1)
        selected['GATED mean ± SD']=selected.apply(lambda r:shared.mean_sd(r.gated_mean,r.gated_sd,r.gated_n),axis=1)
        model_table=shared.markdown_table(selected[['condition','metric','GCN mean ± SD','GATED mean ± SD']])
        plots+=comparison_figures(output,frame,gated)
        both=[]
        for label,data in [('GCN',frame),('GATED',gated)]:
            from evaluate import aggregate
            _,contrast=aggregate(data,[m for m in shared.PERFORMANCE if m in data])
            both.append(contrast[contrast.condition=='randomized'].assign(architecture=label))
        pd.concat(both,ignore_index=True).to_csv(output/'original_vs_randomized_by_architecture.csv',index=False,na_rep='N/A')
    graph=frame[['condition','node_count','biological_relation_count','directed_edge_count','original_edges_retained_percent','degree_exact_preservation_fraction']].drop_duplicates('condition')
    unavailable=pd.read_csv(output/'metric_availability.csv',keep_default_na=False)
    unavailable=unavailable[unavailable.status=='N/A'][['metric','reason']].drop_duplicates()
    result=pd.DataFrame(tables)
    metric_tables='\n\n'.join(shared.markdown_table(result[['Metric']+cols]) for cols in [CONDITIONS[:3],CONDITIONS[3:]])
    contrast_lines=[]
    for m in ['foscttm','matching_recall_at_1','avg_silhouette_width','label_transfer_rna_to_atac_macro_f1']:
        part=contrasts[contrasts.metric==m]
        if len(part) and not smoke:
            r=part.iloc[0];contrast_lines.append('{}: original {:.5f}, randomized {:.5f}; seed-matched change {:+.5f} ± {:.5f} sample SD.'.format(m,r.baseline_mean,r['mean'],r.seed_matched_difference_mean,r.seed_matched_difference_sd))
    method='The metric functions, parameters and PCA/LSI reference hashes match the completed GATED evaluation exactly. FOSCTTM uses bidirectional strict closer-than-true Euclidean distance counts divided by N; recall@1/@5/@10 retrieves the verified true barcode counterpart. Embeddings are joined by identifier. Biological conservation includes scaled/raw cell-type ASW, cell-type connectivity, Leiden NMI/ARI, neighborhood conservation and bidirectional 15-NN annotation transfer. Modality mixing includes within-type modality ASW and iLISI. cLISI closer to 1 is better. WNN-derived cell types are reference annotations, and transfer measures concordance. The fixed-k Pearson modality diagnostic is not canonical R kBET. Independent donor/batch metrics and canonical R kBET remain N/A.'
    parts=['# Original GCN-GLUE: graph subsampling and degree-preserving randomized control',
        '**SMOKE VALIDATION ONLY: sampled cells and bounded training; no full-training result.**' if smoke else '**18 completed original GCN runs: six conditions × three model seeds, graph seed 0; matched comparison with 18 completed GATED runs.**',
        'The experiment measures sensitivity to biological guidance endpoint identity and relation removal. '+(' '.join(contrast_lines) if contrast_lines else 'This smoke verifies randomized-graph original GCN training, reloadable checkpoints, embeddings and gate-free evaluation.'),
        '## Architecture and matched preprocessing',
        'The unchanged original GLUE repository runner instantiates sc.GraphEncoder with nn.GraphConv, the original graph decoder, NB modality decoders and original loss functions. No gates, attention or GATED regularization are introduced. Constructed models and loaded checkpoints are audited. RNA HVG/PCA, ATAC all-peak LSI, pretraining, balancing, fine-tuning and automatic full-training schedule match the existing 15 GCN runs. Shared parameters: '+json.dumps(SHARED,sort_keys=True)+'. Full model seeds are 0,1,2; graph seed 0. The smoke bounds pretraining to 50 epochs and fine-tuning to two epochs.',
        '## Exact randomized graph verification',
        'The prior and perturbation code SHA256 match the completed GATED evaluation. Exactly 134,930 accepted reciprocal bipartite endpoint swaps use graph_seed=0 and swap_multiplier=10. The graph retains 15,205 nodes/self-loops, 13,493 biological pairs and 42,191 directed edges. All per-node non-loop in/out-degrees are preserved. Exactly 22 original relations overlap (0.1630475061%). Complete directed edge attributes match deterministic GATED reconstructions for all three seeds; actual saved GATED checkpoint endpoints match all 42,191 edge identities. Checkpoints store endpoints; complete provenance attributes dist/id are verified through the hash-verified deterministic reconstruction, and are not biological distances after rewiring. Uniform weight=1/sign=1 semantics are preserved. Evidence: randomized_control/validation/graph_verification.json.',
        shared.markdown_table(graph),
        '## Evaluation methodology',method,'Recorded parameters: '+json.dumps(config['parameters'],sort_keys=True)+'.',
        'Means and sample SD use ddof=1 over model seeds. Seed-matched changes are descriptive training variability, not significance tests. N/A values remain missing; gate-specific diagnostics remain exclusive to the separate completed GATED report.',
        '## GCN per-condition metrics',metric_tables,
        '## Original versus randomized', '\n\n'.join(contrast_lines) if contrast_lines else 'No full-data interpretation from smoke validation.',
        '## GCN versus GATED',model_table,
        '## Graph subsampling sensitivity',
        'Retention curves show the five unchanged nested subsets only. Randomization preserves graph size and is compared separately. Exact-cell matching, biological conservation and modality mixing can respond differently. See per-seed plots and mean ± SD; no gate mechanism is inferred from a model comparison.',
        '## Availability and limitations', shared.markdown_table(unavailable),
        'One PBMC dataset, one graph seed and three model seeds limit generalization. Nested subsets are dependent. WNN annotations are not independent biological ground truth. Pair metrics evaluate unsupervised embeddings using verified correspondence. Original GCN and GATED differ in propagation architecture and gate parameters; shared compatible settings and metric definitions are matched.',
        '## Provenance and output preservation',
        'The original manifest and launchers remain frozen. Existing jobs 64840335 and 64840336 are unchanged. Three fresh randomized runs have separate training directories. The combined evaluator requires all 18 completion records and validated checkpoints/embeddings, and is submitted with afterok dependencies on both training arrays. Its job-specific report directory preserves earlier reports. Source, input and evaluation fingerprints prohibit incompatible checkpoint reuse.',
        '## Figures','\n\n'.join('![{}](figures/{}.png)'.format(n.replace('_',' '),n) for n in plots)]
    (output/'REPORT.md').write_text('\n\n'.join(parts)+'\n')
    (output/'methodology.md').write_text(method+'\n\n'+json.dumps(config['parameters'],indent=2)+'\n')
    shutil.copyfile(EXPERIMENT/'README.md',output/'README.md')
    (output/'figure_inventory.csv').write_text('figure,png,pdf\n'+''.join('{0},figures/{0}.png,figures/{0}.pdf\n'.format(n) for n in plots))
    success=False
    if shutil.which('pandoc') and shutil.which('pdflatex'):
        proc=subprocess.run(['pandoc','REPORT.md','-o','REPORT.pdf','--pdf-engine=pdflatex','-V','geometry:margin=.55in','-V','fontsize=9pt'],cwd=str(output),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (output/'pdf_build.log').write_text(proc.stdout);success=proc.returncode==0
    if not success:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        lines=[]
        for line in (output/'REPORT.md').read_text().splitlines():
            if not line.startswith('!['): lines.extend(textwrap.wrap(line,108) or [''])
        with PdfPages(output/'REPORT.pdf') as pdf:
            for start in range(0,len(lines),64):
                fig=plt.figure(figsize=(11.7,8.3));fig.text(.04,.96,'\n'.join(lines[start:start+64]),va='top',family='DejaVu Sans Mono',fontsize=7)
                pdf.savefig(fig);plt.close(fig)
            for name in plots:
                fig=plt.figure(figsize=(11.7,8.3));ax=fig.add_subplot(111);ax.imshow(plt.imread(output/'figures'/(name+'.png')));ax.axis('off');pdf.savefig(fig);plt.close(fig)
    (output/'pdf_status.txt').write_text('pandoc/pdflatex with figures\n' if success else 'Matplotlib PDF including all report figures; separate vector PDFs in figures/\n')


if __name__=='__main__':
    import sys
    generate(sys.argv[1])
