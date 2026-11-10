"""Scientific reporting for the five original GCN retention conditions."""
import json
from pathlib import Path
import shutil
import subprocess
import textwrap

import pandas as pd
from scipy.stats import spearmanr

from common import EXPERIMENT,CONDITIONS,SHARED
import reporting as shared


def generate(output):
    output=Path(output)
    frame=pd.read_csv(output/'per_run_metrics.csv',na_values=['N/A'])
    summary=pd.read_csv(output/'summary_metrics.csv',na_values=['N/A'])
    comparison=pd.read_csv(output/'baseline_comparison.csv',na_values=['N/A'])
    config=json.loads((output/'evaluation_config.json').read_text())
    smoke=config['evaluation_mode']=='smoke'
    if not smoke and (len(frame)!=15 or set(frame.condition)!=set(CONDITIONS)):
        raise ValueError('Full GCN report requires all 15 completed runs')
    if any(c.startswith('gate_') for c in frame.columns): raise ValueError('GCN report cannot contain gate metrics')
    plots=shared.figures(output,frame,summary,order=CONDITIONS)
    tables=[];rankings=[]
    for metric,(label,higher) in shared.PERFORMANCE.items():
        part=summary[summary.metric==metric].set_index('condition')
        if len(part)==0:continue
        entry={'Metric':label}
        for condition in CONDITIONS:
            if condition in part.index:
                r=part.loc[condition];entry[condition]=shared.mean_sd(r['mean'],r['sd'],r['n'])
            else:entry[condition]='N/A'
        tables.append(entry)
        ranked=part.reset_index();ranked['rank']=ranked['mean'].rank(ascending=not higher,method='min')
        ranked['direction']='higher better' if higher else 'lower better';rankings.append(ranked)
    pd.concat(rankings,ignore_index=True).to_csv(output/'condition_rankings.csv',index=False,na_rep='N/A')
    trends=[];changes=[]
    if not smoke:
        for metric in ['foscttm','matching_recall_at_1','avg_silhouette_width','avg_silhouette_width_batch','label_transfer_rna_to_atac_macro_f1']:
            part=frame.groupby('condition').agg(retention=('edge_count_fraction','mean'),score=(metric,'mean'))
            rho=spearmanr(part.retention,part.score)[0]
            trends.append('{}: retention versus the five condition means has descriptive Spearman rho={:.3f}.'.format(metric,rho))
            r=comparison[(comparison.metric==metric)&(comparison.condition=='retain_10')].iloc[0]
            changes.append('{}: original mean {:.4f}; 10% mean {:.4f}; seed-matched change {:+.4f} ± {:.4f} sample SD.'.format(metric,r.baseline_mean,r['mean'],r.seed_matched_difference_mean,r.seed_matched_difference_sd))
    graph=frame[['condition','biological_relation_count','edge_count_fraction','directed_edge_count','node_count','original_edge_retained_fraction','degree_mean_absolute_change']].drop_duplicates('condition')
    graph.columns=['Condition','Biological pairs','Count fraction','Directed edges','Nodes','Original pair overlap fraction','Mean degree change']
    availability=pd.read_csv(output/'metric_availability.csv',keep_default_na=False)
    unavailable=availability[availability.status=='N/A'][['metric','reason']].drop_duplicates()
    # Split wide results into two tables so the typeset report stays readable.
    result=pd.DataFrame(tables)
    result_tables='\n\n'.join(shared.markdown_table(result[['Metric']+cols]) for cols in [CONDITIONS[:3],CONDITIONS[3:]])
    parts=['# Original GLUE GCN: PBMC guidance relation subsampling',
        '**SMOKE VALIDATION ONLY: sampled cells, bounded 50-epoch pretraining and two-epoch fine-tuning; no full-experiment conclusion.**' if smoke else '**15 completed runs: five graph retentions × three model seeds; graph seed 0.**',
        '## Executive summary',
        'This experiment asks how removing signed biological guidance relations affects original GLUE integration. Exact-cell alignment, cell-type biological conservation, and modality mixing are reported separately. '+(' '.join(changes[:2]) if changes else 'The smoke output verifies original-model training, checkpoint/embedding saving, and evaluation without gate diagnostics.'),
        '## Architecture and experimental configuration',
        'The unchanged original repository SCGLUEModel instantiates sc.GraphEncoder with nn.GraphConv, the original Bernoulli graph decoder, NB RNA/ATAC likelihoods, and the original graph/adversarial objectives. Actual constructed instances and reloaded checkpoints are audited before fitting and evaluation. There are no learnable edge gates, attention modules or gate regularizers. The original runner performs pretraining, balancing-weight estimation, pretrained weight adoption and fine-tuning.',
        'Shared training settings: '+json.dumps(SHARED,sort_keys=True)+'. Model seeds 0,1,2; graph seed 0. All three original-graph baselines are freshly trained from the frozen original source; historical candidates lacked frozen preprocessing/source provenance adequate for reuse.',
        'RNA and ATAC contain the same 9,631 source Multiome barcodes in the full experiment, verified against the source collection notebook, protocol, sample metadata and embedding IDs. The model trains without pair supervision; exact-cell metrics use verified correspondence at evaluation. The 19 cell-type reference annotations come from annotated joint WNN clusters and are not independent experimental ground truth.',
        '## Guidance graph perturbation',
        'The existing subsample_reciprocal_pairs implementation uniformly retains floor(f × 13,493) reciprocal biological pairs with graph_seed=0. The five fixed graphs retain 13,493, 10,119, 6,746, 3,373 and 1,349 pairs. All 15,205 nodes and self-loops, signs, retained weights and reciprocal relationships are preserved. Smaller subsets are nested. Actual saved GATED checkpoint edge identities were compared with these prepared graphs; the model seeds do not independently resample graph edges.',
        shared.markdown_table(graph),
        '## Evaluation methodology',
        'The same PBMC metric functions and the exact recorded settings from the completed GATED evaluation are reused. Parameters: '+json.dumps(config['parameters'],sort_keys=True)+'. Full neighborhood conservation uses the exact GATED evaluation 50D PCA/LSI reference files, verified by SHA256 and aligned by ID. No gate behavior metric is computed or required.',
        'FOSCTTM measures the directional fraction of targets closer than the true counterpart (strict inequality, denominator N), averaged across assays; lower is better. Matching recall@1/@5/@10 measures exact counterpart retrieval; higher is better. Both use chunked exact Euclidean distances. MNN uses cross-assay kNN mutuality; nearest-type agreement and bidirectional label transfer quantify reference annotation concordance, not exact cell matching.',
        'Raw biological ASW is in [-1,1]; scaled GLUE ASW=(raw+1)/2 is in [0,1], higher better. Within-type modality ASW averages 1−|silhouette|, higher mixing. Coordinate LISI uses perplexity-weighted exp(−beta*d) probabilities and inverse Simpson diversity; modality iLISI higher better, cell-type cLISI closer to 1 better. Cell-type connectivity is the macro largest-component fraction on Scanpy k=15 connectivities.',
        'Fixed-resolution Leiden NMI/ARI use evaluation seed and resolution from the recorded configuration. Legacy maximum NMI over resolutions 0.1..2.0 is additionally reported as label-selected and exploratory. Neighborhood conservation uses original GLUE within-assay neighbor Jaccard with neighbor fraction .01. Label transfer uses uniform 15-NN voting in each direction, accuracy, macro-F1 and balanced accuracy; true counterparts remain in the target pool.',
        '## Results: mean and sample SD',
        'All run-level values are retained in per_run_metrics.csv. Means/SD summarize three model seeds using ddof=1. N/A is never zero; singleton smoke SD is N/A. Signed/centered metrics and zero baselines do not receive misleading percent changes.',
        result_tables,
        '## Retention sensitivity and baseline contrasts',
        '\n\n'.join(trends+changes) if trends else 'No retention trend is interpreted from the smoke test.',
        'Condition rankings are descriptive. A decline in exact-cell retrieval may differ from a change in annotated cell-type structure; technical mixing alone does not establish correct alignment or retained biological information.',
        '## Reproducibility and limitations',
        'One dataset and one graph seed limit generalization. Nested graph subsets are dependent. Three model seeds describe training variability and do not establish statistical significance. Cells and edges are not independent experiment replicates. WNN annotation dependence can inflate annotation-based concordance; transfer is not a held-out prediction benchmark. Independent donor/batch labels are absent. Original GCN and GATED differ in graph propagation and gate-related parameters; shared compatible non-graph settings and evaluation definitions are matched.',
        shared.markdown_table(unavailable),
        'Original and wrapper source hashes, frozen graph hashes, per-run arguments, model construction proofs, versions, evaluation parameters, pairing evidence and reference hashes are recorded in the experiment validation directory and report provenance files. Checkpoint reuse is allowed only with matching fingerprints. No GATED training output is changed.',
        '## Conclusions',
        'The full retention contrasts characterize original GCN-GLUE sensitivity for this fixed PBMC setup. '+(' '.join(changes[:2]) if changes else 'The smoke run supports implementation validation only.')+' Replication across guidance graph seeds and datasets is required for broader thesis claims.',
        '## Figures',
        '\n\n'.join('![{}](figures/{}.png)'.format(n.replace('_',' '),n) for n in plots),
        '## Sources',
        'Original GLUE: scglue/models/scglue.py, sc.py, nn.py, metrics.py and evaluation/workflow/scripts/run_GLUE.py in the original repository. Perturbation: GLUE_GATED_PBMC/evaluation/workflow/scripts/graph_perturbation.py. Metric mathematical details follow the shared PBMC scripts/methodology.md; gate and randomized-control sections of that shared document do not apply to this GCN experiment.']
    (output/'REPORT.md').write_text('\n\n'.join(parts)+'\n')
    shutil.copyfile(EXPERIMENT/'README.md',output/'README.md')
    (output/'methodology.md').write_text('\n\n'.join(parts[parts.index('## Evaluation methodology'):parts.index('## Results: mean and sample SD')])+'\n')
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
            if not line.startswith('!['):lines.extend(textwrap.wrap(line,108) or [''])
        with PdfPages(output/'REPORT.pdf') as pdf:
            for start in range(0,len(lines),64):
                fig=plt.figure(figsize=(11.7,8.3));fig.text(.04,.96,'\n'.join(lines[start:start+64]),va='top',family='DejaVu Sans Mono',fontsize=7)
                pdf.savefig(fig);plt.close(fig)
    (output/'pdf_status.txt').write_text('pandoc/pdflatex with figures\n' if success else 'Matplotlib text PDF; vector figures in figures/\n')
