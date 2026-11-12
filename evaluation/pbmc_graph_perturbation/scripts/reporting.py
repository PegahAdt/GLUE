"""Tables, publication figures, and evidence-led reporting from evaluated runs."""
import json
from pathlib import Path
import shutil
import subprocess
import textwrap

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ORDER = ['original','retain_75','retain_50','retain_25','retain_10','randomized']
LABELS = ['Original','75%','50%','25%','10%','Randomized']
# Metric direction is explicit; counts and diagnostic parameters are not ranked.
PERFORMANCE = {
    'foscttm': ('FOSCTTM', False),
    'matching_recall_at_1': ('Matching recall@1', True),
    'matching_recall_at_5': ('Matching recall@5', True),
    'matching_recall_at_10': ('Matching recall@10', True),
    'cross_nn_cell_type_agreement': ('Cross-modal cell-type agreement', True),
    'avg_silhouette_width': ('Cell-type ASW (scaled)', True),
    'avg_silhouette_width_batch': ('Modality ASW within cell type', True),
    'ilisi': ('iLISI (modality)', True),
    'clisi': ('cLISI', False),
    'graph_connectivity': ('Cell-type graph connectivity', True),
    'nmi_leiden_fixed': ('NMI (Leiden res. 1)', True),
    'ari_leiden_fixed': ('ARI (Leiden res. 1)', True),
    'normalized_mutual_info': ('NMI (optimized, exploratory)', True),
    'label_transfer_rna_to_atac_macro_f1': ('RNA to ATAC macro-F1', True),
    'label_transfer_atac_to_rna_macro_f1': ('ATAC to RNA macro-F1', True),
    'neighbor_conservation': ('Neighborhood conservation', True),
    'mean_average_precision': ('Cell-type MAP', True),
    'seurat_alignment_score': ('Seurat modality alignment', True),
    'kbet_modality_fixed_k_rejection': ('Fixed-k modality rejection', False)
}


def markdown_table(frame):
    # Avoid an optional tabulate dependency.
    def cell(v):
        if pd.isna(v): return 'N/A'
        return str(v).replace('|','/').replace('\n',' ')
    columns = list(frame.columns)
    return '\n'.join(['| '+' | '.join(map(str,columns))+' |', '| '+' | '.join(['---']*len(columns))+' |'] +
                     ['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)])


def mean_sd(mean, sd, n):
    if pd.isna(mean): return 'N/A'
    return '{:.4f} ± {:.4f} (n={})'.format(mean,sd,int(n)) if pd.notna(sd) else '{:.4f}; SD N/A (n={})'.format(mean,int(n))


def figures(output, frame, summary, order=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'ps.fonttype':42,'savefig.dpi':350})
    dest = output/'figures'
    dest.mkdir(exist_ok=True)
    files = []
    condition_order=ORDER if order is None else order
    def save(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf']:
            fig.savefig(dest/(name+'.'+ext),bbox_inches='tight')
        plt.close(fig)
        files.append(name)
    available = [m for m in PERFORMANCE if m in frame and frame[m].notna().any()]
    if not available: return []
    selected = [m for m in ['foscttm','matching_recall_at_1','avg_silhouette_width','avg_silhouette_width_batch','ilisi','label_transfer_rna_to_atac_macro_f1'] if m in available]
    def bars(metrics,name,title,conditions=None):
        if conditions is None: conditions=condition_order
        fig,axes = plt.subplots(int(np.ceil(len(metrics)/3)),min(3,len(metrics)),figsize=(13,3.5*int(np.ceil(len(metrics)/3))),squeeze=False)
        for ax,metric in zip(axes.flat,metrics):
            part = summary[summary.metric == metric].set_index('condition').reindex(conditions)
            xpos = np.arange(len(conditions))
            ax.bar(xpos,part['mean'],color='#407a9c',alpha=.65)
            for i,c in enumerate(conditions):
                points = frame.loc[frame.condition == c,metric].dropna()
                jitter = np.linspace(-.12,.12,len(points))
                ax.scatter(i+jitter,points,color='#173f54',s=20,zorder=3)
            valid = part['sd'].notna() & part['mean'].notna()
            ax.errorbar(xpos[valid],part.loc[valid,'mean'],yerr=part.loc[valid,'sd'],fmt='none',capsize=3,color='black')
            ax.set_xticks(xpos)
            ax.set_xticklabels([LABELS[ORDER.index(c)] for c in conditions],rotation=30,ha='right')
            ax.set_ylabel(PERFORMANCE[metric][0])
            ax.set_title('Higher better' if PERFORMANCE[metric][1] else 'Lower better')
        for ax in list(axes.flat)[len(metrics):]: ax.set_visible(False)
        fig.suptitle(title+'\nDots: model seeds; error bars: sample SD',fontsize=13)
        save(fig,name)
    bars(available,'all_condition_metrics','Metrics across guidance graph conditions')
    bars(selected,'seed_variability','Integration and biological conservation')
    if set(['original','randomized']) <= set(frame.condition):
        bars(selected,'original_vs_randomized','Original versus degree-preserving randomized graph',['original','randomized'])
    retention = frame[frame.condition != 'randomized']
    fig,axes = plt.subplots(2,3,figsize=(13,7),squeeze=False)
    for ax,metric in zip(axes.flat,selected):
        for seed,g in retention.groupby('model_seed'):
            g = g.sort_values('edge_count_fraction')
            ax.plot(100*g.edge_count_fraction,g[metric],marker='o',alpha=.45,label='Seed {}'.format(seed))
        groups = retention.groupby('edge_count_fraction')[metric]
        mean,sd = groups.mean(),groups.std(ddof=1)
        ax.errorbar(100*mean.index,mean.values,yerr=sd.fillna(0).values,fmt='o-',color='black',capsize=3,label='Mean ± SD')
        ax.set_xlabel('Biological relation count retained (%)')
        ax.set_ylabel(PERFORMANCE[metric][0])
    for ax in list(axes.flat)[len(selected):]: ax.set_visible(False)
    axes.flat[0].legend(fontsize=8)
    fig.suptitle('Graph retention sensitivity'+(' (randomized control excluded)' if 'randomized' in condition_order else ''))
    save(fig,'retention_sensitivity')
    if {'avg_silhouette_width','avg_silhouette_width_batch'} <= set(available):
        fig,ax = plt.subplots(figsize=(7,5))
        for condition in condition_order:
            g=frame[frame.condition == condition]
            if len(g): ax.scatter(g.avg_silhouette_width_batch,g.avg_silhouette_width,label=LABELS[ORDER.index(condition)],s=45)
        ax.set_xlabel('Modality ASW within cell type (higher = more mixing)')
        ax.set_ylabel('Scaled cell-type ASW (higher = more separation)')
        ax.set_title('Biological conservation versus modality mixing')
        ax.legend(fontsize=8,bbox_to_anchor=(1.02,1),loc='upper left')
        save(fig,'biology_vs_mixing')
    gates = [m for m in ['gate_mean','gate_median','gate_sd','gate_fraction_lt_0_5','gate_q05','gate_reciprocal_mean_abs_difference'] if m in frame and frame[m].notna().any()]
    if gates:
        fig,axes=plt.subplots(2,3,figsize=(13,7),squeeze=False)
        for ax,metric in zip(axes.flat,gates):
            for condition in condition_order:
                g=frame[frame.condition == condition]
                if len(g): ax.scatter(g.perturbation_strength,g[metric],label=LABELS[ORDER.index(condition)],s=30)
            ax.set_xlabel('Perturbation strength: 1 − original pair overlap')
            ax.set_ylabel(metric.replace('_',' '))
        for ax in list(axes.flat)[len(gates):]: ax.set_visible(False)
        axes.flat[0].legend(fontsize=7)
        fig.suptitle('Gate behavior across graph conditions')
        save(fig,'gate_behavior')
    # Remove constant/absent columns. Run-level correlations confound condition effects.
    corr_names = [m for m in selected+['gate_mean','gate_sd','gate_fraction_lt_0_5','perturbation_strength'] if m in frame and frame[m].nunique() > 1]
    if len(corr_names) > 1 and len(frame) > 2:
        corr=frame[corr_names].corr(method='spearman')
        corr.to_csv(output/'metric_correlations.csv',na_rep='N/A')
        fig,ax=plt.subplots(figsize=(10,8))
        im=ax.imshow(corr,vmin=-1,vmax=1,cmap='coolwarm')
        names=[PERFORMANCE[m][0] if m in PERFORMANCE else m.replace('_',' ') for m in corr_names]
        ax.set_xticks(range(len(names))); ax.set_yticks(range(len(names)))
        ax.set_xticklabels(names,rotation=55,ha='right'); ax.set_yticklabels(names)
        for i in range(len(names)):
            for j in range(len(names)):
                if pd.notna(corr.iloc[i,j]): ax.text(j,i,'{:.2f}'.format(corr.iloc[i,j]),ha='center',va='center',fontsize=8)
        ax.set_title('Exploratory Spearman correlations across runs\nCondition effects and shared graph realizations confound these correlations')
        fig.colorbar(im,ax=ax,label='Spearman rho')
        save(fig,'metric_correlation_heatmap')
    return files


def generate_report(output):
    output=Path(output)
    frame=pd.read_csv(output/'per_run_metrics.csv',na_values=['N/A'])
    summary=pd.read_csv(output/'summary_metrics.csv',na_values=['N/A'])
    comparison=pd.read_csv(output/'baseline_comparison.csv',na_values=['N/A'])
    availability=pd.read_csv(output/'metric_availability.csv',keep_default_na=False)
    config=json.loads((output/'evaluation_config.json').read_text())
    data=json.loads((output/'dataset_metadata.json').read_text())
    pair=json.loads((output/'pairing_verification.json').read_text())
    smoke=config['evaluation_mode'] == 'smoke'
    expected=18
    if not smoke and len(frame) != expected:
        raise ValueError('Refusing a full scientific report from incomplete run tables')
    plots=figures(output,frame,summary)
    ranking=[]
    for metric,(label,higher) in PERFORMANCE.items():
        part=summary[(summary.metric == metric)&(summary['n'] > 0)].copy()
        part['rank']=part['mean'].rank(ascending=not higher,method='min')
        part['direction']='higher better' if higher else 'lower better'
        ranking.append(part)
    pd.concat(ranking,ignore_index=True).to_csv(output/'condition_rankings.csv',index=False,na_rep='N/A')
    table=[]
    for metric,(label,_) in PERFORMANCE.items():
        part=summary[summary.metric == metric].set_index('condition')
        if part.empty: continue
        entry={'Metric':label}
        for condition in ORDER:
            if condition in part.index:
                r=part.loc[condition]
                entry[condition]=mean_sd(r['mean'],r['sd'],r['n'])
            else: entry[condition]='N/A'
        table.append(entry)
    # Trends are descriptive, without significance tests across three training seeds.
    trends=[]
    for metric in ['foscttm','matching_recall_at_1','avg_silhouette_width','avg_silhouette_width_batch','label_transfer_rna_to_atac_macro_f1']:
        part=summary[(summary.metric == metric)&summary.condition.ne('randomized')].set_index('condition')
        retained=[]
        for condition in ORDER[:-1]:
            g=frame[frame.condition == condition]
            if len(g) and condition in part.index and pd.notna(part.loc[condition,'mean']):
                retained.append((g.edge_count_fraction.iloc[0],part.loc[condition,'mean']))
        if len(retained) >= 3:
            rho=spearmanr(*zip(*retained))[0]
            trends.append('{}: Spearman rho between realized retention and the five condition means = {:.3f} (descriptive).'.format(PERFORMANCE[metric][0],rho))
    comparisons=[]
    for metric in ['foscttm','matching_recall_at_1','avg_silhouette_width','avg_silhouette_width_batch','label_transfer_rna_to_atac_macro_f1','gate_mean']:
        r=comparison[(comparison.metric == metric)&(comparison.condition == 'randomized')]
        if len(r) and pd.notna(r.iloc[0]['mean']):
            r=r.iloc[0]
            comparisons.append('{}: original mean {:.4f}; randomized mean {:.4f}; change {:+.4f}; seed-matched change SD {:.4f}.'.format(metric,r.baseline_mean,r['mean'],r.seed_matched_difference_mean,r.seed_matched_difference_sd))
    observations=[]
    if not smoke:
        for metric,(label,higher) in PERFORMANCE.items():
            part=summary[(summary.metric==metric)&(summary['n']>0)]
            if len(part)<2: continue
            best=part.loc[part['mean'].idxmax() if higher else part['mean'].idxmin()]
            original=part[part.condition=='original']
            if best.condition!='original' and len(original):
                observations.append('{} has its best observed mean in {} ({:.4f}, versus original {:.4f}); the ranking is descriptive.'.format(label,best.condition,best['mean'],original.iloc[0]['mean']))
        observations=observations[:6]
    gate_relationships=[]
    for metric in ['foscttm','avg_silhouette_width','avg_silhouette_width_batch']:
        if metric in frame and frame[metric].nunique()>1 and frame.gate_mean.nunique()>1:
            rho=spearmanr(frame.gate_mean,frame[metric],nan_policy='omit')[0]
            gate_relationships.append('Across runs, gate mean versus {} has descriptive Spearman rho={:.3f}; condition effects are not controlled.'.format(metric,rho))
    na=availability[availability.status == 'N/A'][['metric','reason']].drop_duplicates()
    graph=frame[['condition','biological_relation_count','directed_edge_count','original_edges_retained_percent','edge_jaccard','degree_exact_preservation_fraction','degree_distribution_ks']].drop_duplicates('condition')
    for c in graph.columns[1:]: graph[c]=graph[c].map(lambda v:'{:.5g}'.format(v))
    gate=[]
    for metric in ['gate_mean','gate_median','gate_sd','gate_q05','gate_fraction_lt_0_5','gate_fraction_ge_0_95','gate_reciprocal_mean_abs_difference']:
        part=summary[summary.metric == metric].set_index('condition')
        entry={'Statistic':metric}
        for condition in ORDER:
            if condition in part.index:
                r=part.loc[condition]; entry[condition]=mean_sd(r['mean'],r['sd'],r['n'])
        gate.append(entry)
    title='PBMC guidance graph robustness evaluation'
    report=['# '+title,
        '**SMOKE TEST: one sampled run; these are validation outputs, not thesis results.**' if smoke else '**Full evaluation: 18 runs, six graph conditions, three model seeds per condition.**',
        '## 1. Executive summary',
        'The evaluation separates paired-cell alignment, conservation of annotated biological structure, modality mixing, guidance graph topology, and learned gate behavior. All reported differences are descriptive. Three model seeds and one fixed graph realization per condition do not establish statistical significance or population-level robustness.',
        ' '.join(comparisons[:2]) if comparisons else 'The smoke sample supports pipeline validation only.',
        '## 2. Research questions and hypotheses',
        'Does integration quality change as guidance relations are removed? Does preserving degree while disrupting biological endpoints preserve integration? Do gates respond to graph perturbations, and do gate summaries track alignment or biological conservation? The hypotheses are that informative graph topology supports alignment and that gate adaptation may buffer some perturbations. These hypotheses must be assessed from measured outcomes; no causal gate mechanism is established by these runs.',
        '## 3. Dataset and experimental configuration',
        'Source data: 10x Multiome PBMC; RNA cells: {}; ATAC cells: {}. There are {} reference cell types. Labels originate from annotated Seurat WNN clusters formed using both modalities. They are useful biological reference annotations but are not independent experimental ground truth; label transfer and annotation concordance can inherit that dependence.'.format(data['rna']['n_cells'],data['atac']['n_cells'],len(data['rna']['cell_type_counts'])),
        'Pairing verification: '+pair['reason']+'. Training treats the assays as unpaired; evaluation may use verified source correspondence. Modality labels identify RNA versus ATAC. The constant SeuratProject identifier provides no independent donor or batch contrast.',
        'Shared training configuration: GATED encoder, latent dim 50, alt_dim 100, hidden depth 2, hidden dim 256, dropout 0.2, graph weight 0.02, alignment weight 0.05, learning rate 0.002, 10 negative samples, cell batch size 128, gate initialization 0.95, lam_keep 0. Model seeds 0, 1, 2; graph seed 0. The authoritative complete arguments remain in each run_info.yaml.',
        '## 4. Graph perturbation methodology',
        'Uniform reciprocal relation subsampling uses floor(f*N) biological pairs and nested seeded subsets. All nodes and self-loops remain. The randomized control uses 10*N accepted bipartite reciprocal endpoint swaps, preserves per-node non-loop degree, and can retain some original pairs. Graphs are reconstructed with the original implementation and every saved perturbation metadata field is verified. Randomized graph edge count is 100% of original; biological pair overlap is a separate quantity.',
        markdown_table(graph),
        '## 5. Metrics and mathematical definitions',
        'See [methodology.md](methodology.md) for exact formulas, directions, validity criteria, clustering resolution, random seeds, and differences from the legacy GLUE evaluator. Distances use unnormalized saved latent coordinates and Euclidean distance. Integration is not scored using UMAP coordinates. Cell-type ASW is reported both raw and scaled; modality ASW is computed within each reference cell type.',
        '## 6. Results: condition means and sample SD',
        'Cells are not independent experiment replicates. Tables below summarize model seeds using ddof=1. Per-run results and metric availability are in the CSV files; N/A is never replaced by zero. Optimized NMI selects resolution using labels and is exploratory; fixed-resolution NMI/ARI provide a complementary, reproducible comparison.',
        markdown_table(pd.DataFrame(table)),
        '\n\n'.join(observations) if observations else 'No additional cross-condition ranking is interpreted from a single smoke run.',
        '## 7. Graph retention sensitivity',
        '\n\n'.join(trends) if trends else 'Sensitivity trends are not assessed from the smoke test.',
        'The randomized control is excluded from retention curves because it preserves edge count while changing endpoint identity. Nonmonotone trends are possible and should be discussed as observations rather than evidence of a mechanism. Nested subsets are dependent, and only one graph seed was used.',
        '## 8. Original versus randomized graph',
        '\n\n'.join(comparisons) if comparisons else 'Requires both completed conditions.',
        'The control tests the role of endpoint topology under preserved degree. It is not a no-graph control. Differences can involve downstream training randomness as well as the fixed topology intervention.',
        '## 9. Gate behavior',
        'Individual directed non-loop gates are read from trusted final.dill model weights on CPU. Gate topology and mean are checked against the reconstructed graph and YAML diagnostics. Self-loop gates fixed at one are excluded. Threshold fractions describe soft gate distributions, not physical deletion of guidance edges. No weight update or model training is performed.',
        markdown_table(pd.DataFrame(gate)),
        '\n\n'.join(gate_relationships) if gate_relationships else 'Gate/performance associations require multiple evaluated runs.',
        'Metric/gate correlations are exploratory across 18 dependent runs, confounded by condition and shared graph topology. High average gates alone do not establish correct biological guidance or a causal robustness mechanism. Reciprocal directional gates are dependent and are not biological replicates.',
        '## 10. Biological versus technical interpretation',
        'Better modality mixing can coexist with worse cell-type separation or paired-cell matching. Interpret iLISI/modality ASW alongside biological ASW, cLISI, cell-type transfer, graph connectivity, and FOSCTTM. Overmixing unrelated biological populations can improve a technical metric. Conversely, perfect cell-type concordance does not prove correct cell correspondence. Matching recall and FOSCTTM address that finer alignment.',
        '## 11. Reproducibility and limitations',
        'Evaluation seed {}; Leiden fixed resolution {}; Scanpy neighbors k=15; cross-modal k={}; LISI perplexity {}; fixed-k Pearson modality test k={}; distance chunk {}; sklearn working memory {} MiB. Source/data hashes, versions, complete CLI configuration and verified pairing are recorded in evaluation_config.json. Derived unimodal reference provenance is recorded separately. Checkpoints are reused only under the same fingerprint.'.format(config['evaluation_seed'],config['leiden_resolution'],config['cross_k'],config['lisi_perplexity'],config['kbet_k'],config['chunk_size'],config['working_memory_mb']),
        'Limitations: three training seeds; one graph realization per condition; one PBMC dataset; annotation dependence on joint WNN; no independent donor/batch annotation; no hypothesis-testing claim; software/hardware differences can change floating point or approximate Scanpy neighbor outcomes. Matching/label transfer include true counterparts in the target pool; label transfer is annotation concordance rather than a held-out predictive benchmark. Derived 50D PCA/LSI references follow the legacy evaluation workflow, not the 100D training representations.',
        markdown_table(na),
        '## 12. Conclusions for the MSc thesis',
        'The measured contrasts quantify robustness for this fixed PBMC experiment. '+(' '.join(comparisons[:3]) if comparisons else 'No full-dataset conclusion is drawn from smoke validation.')+' Conclusions about general robustness, graph quality, or a gate-mediated causal mechanism require additional datasets, graph seeds, and suitable ablations. Present observed rankings with seed variability and retain the distinction between biological conservation and technical mixing.',
        '## Figures',
        '\n\n'.join('![{}](figures/{}.png)'.format(name.replace('_',' ').capitalize(),name) for name in plots),
        '## References',
        'Local authoritative implementations: scglue/metrics.py; evaluation/workflow/scripts/cell_integration.py; graph_perturbation.py; rna_unirep.py; atac_unirep.py; data/collect/10x-Multiome-Pbmc10k.ipynb; data/download/10x-Multiome-Pbmc10k/wnn.r.',
        '[Harmony/LISI primary paper](https://doi.org/10.1038/s41592-019-0619-0); [LISI reference implementation](https://github.com/immunogenomics/LISI); [kBET primary paper](https://pubmed.ncbi.nlm.nih.gov/30573817/); [kBET reference implementation](https://github.com/theislab/kBET). The fixed-k Pearson variant is explicitly distinguished from canonical kBET.']
    (output/'REPORT.md').write_text('\n\n'.join(report)+'\n')
    shutil.copyfile(Path(__file__).with_name('methodology.md'),output/'methodology.md')
    shutil.copyfile(Path(__file__).with_name('REPRODUCE.md'),output/'README.md')
    (output/'figure_inventory.csv').write_text('figure,png,pdf\n'+''.join('{0},figures/{0}.png,figures/{0}.pdf\n'.format(p) for p in plots))
    # Prefer typeset PDF with all figures. If LaTeX tooling fails, provide a
    # self-contained paginated text PDF and append the actual vector figures.
    pdf_status=''
    if shutil.which('pandoc') and shutil.which('pdflatex'):
        proc=subprocess.run(['pandoc','REPORT.md','-o','REPORT.pdf','--pdf-engine=pdflatex',
                             '-V','geometry:margin=0.55in','-V','fontsize=9pt'],cwd=str(output),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (output/'pdf_build.log').write_text(proc.stdout)
        if proc.returncode == 0: pdf_status='pandoc/pdflatex with figures'
    if not pdf_status:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        lines=[]
        for paragraph in (output/'REPORT.md').read_text().splitlines():
            if paragraph.startswith('!['): continue
            lines.extend(textwrap.wrap(paragraph,width=108) or [''])
        with PdfPages(output/'REPORT.pdf') as pdf:
            for start in range(0,len(lines),64):
                fig=plt.figure(figsize=(11.7,8.3))
                fig.text(.04,.96,'\n'.join(lines[start:start+64]),va='top',family='DejaVu Sans Mono',fontsize=7)
                pdf.savefig(fig); plt.close(fig)
        pdf_status='Matplotlib paginated text PDF; full vector figures are separate in figures/'
    (output/'pdf_status.txt').write_text(pdf_status+'\n')
