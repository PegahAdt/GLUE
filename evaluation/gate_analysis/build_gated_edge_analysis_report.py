#!/usr/bin/env python3
"""Build the supervisor-facing GATED edge-gate report from existing small CSVs."""
from pathlib import Path
import csv, math, statistics

D = Path(__file__).resolve().parent

def rows(name):
    with (D / name).open(newline="") as f:
        return list(csv.DictReader(f))

def esc(x):
    s = str(x)
    for a,b in [("\\","\\textbackslash{}"),("&","\\&"),("%","\\%"),("$","\\$"),("#","\\#"),("_","\\_"),("{","\\{"),("}","\\}"),("~","\\textasciitilde{}"),("^","\\textasciicircum{}")]:
        s=s.replace(a,b)
    return s

def f(x, n=3):
    try:
        v=float(x)
        return "--" if not math.isfinite(v) else f"{v:.{n}f}"
    except (ValueError,TypeError): return esc(x)

def pct(n, den=26986): return f"{100*float(n)/den:.2f}\\%"

def table(headers, data, aligns=None, size="\\scriptsize", long=False):
    aligns = aligns or ("l"*len(headers))
    env = "longtable" if long else "tabular"
    out=[size, f"\\begin{{{env}}}{{{aligns}}}", "\\toprule", " & ".join(headers)+" \\\\", "\\midrule"]
    if long: out += [r"\endfirsthead", r"\toprule", " & ".join(headers)+" \\\\", r"\midrule", r"\endhead", r"\midrule", f"\\multicolumn{{{len(headers)}}}{{r}}{{Continued on next page}} \\\\", r"\endfoot", r"\bottomrule", r"\endlastfoot"]
    out += [" & ".join(map(str,r))+" \\\\" for r in data]
    if not long: out.append(r"\bottomrule")
    out += [f"\\end{{{env}}}", "\\normalsize"]
    return "\n".join(out)

dist=rows("gate_distribution_summary.csv")
full=next(r for r in dist if r["model"]=="full_reference")
ranked=rows("full_reference_ranked_gates.csv")
atten=rows("full_reference_largest_attenuations.csv")
effective=rows("largest_effective_coefficients_full_reference.csv")
robust=rows("robustly_suppressed_edges.csv")
stability8000={(r['source'],r['target']):r for r in rows("gate_stability_size8000.csv")}
seedcorr=rows("seed_rank_correlations.csv")
groups=rows("full_reference_group_summaries.csv")
corrs=rows("full_reference_rank_correlations.csv")
asym=rows("directional_asymmetry_full_reference.csv")
models=rows("models_used.csv")

def edge_rows(src, n, kind):
    z=[]
    for i,r in enumerate(src[:n],1):
        if kind=="low": z.append([i,esc(r['source']),esc(r['target']),esc(r['edge_type']),f(r['prior_sign'],0),f(r['prior_weight']),f(r['normalized_coefficient']),f(r['gate']),f(r['suppression'])])
        elif kind=="att": z.append([i,esc(r['source']),esc(r['target']),esc(r['edge_type']),f(r['normalized_coefficient']),f(r['gate']),f(r['suppression']),f(r['attenuation_of_original_coefficient']),f(r['effective_coefficient'])])
        elif kind=="eff": z.append([i,esc(r['source']),esc(r['target']),esc(r['edge_type']),f(r['prior_sign'],0),f(r['normalized_coefficient']),f(r['gate']),f(r['effective_coefficient']),f(r['absolute_effective_coefficient'])])
        elif kind=="rob": z.append([i,esc(r['source']),esc(r['target']),esc(r['edge_type']),f(r['gate']),f(r['mean_gate']),f(r['sample_sd_gate']),f(min(float(r['mean_gate'])-float(r['sample_sd_gate']),float(r['gate']))),f(max(float(r['mean_gate'])+float(r['sample_sd_gate']),float(r['gate']))),f(1-float(r['mean_gate']))])
    return z

meanrho={s:statistics.mean(float(r['spearman_rho']) for r in seedcorr if r['size']==str(s)) for s in (250,2000,8000)}
minmaxrho={s:(min(float(r['spearman_rho']) for r in seedcorr if r['size']==str(s)),max(float(r['spearman_rho']) for r in seedcorr if r['size']==str(s))) for s in (250,2000,8000)}
normgate=next(r for r in corrs if r['predictor']=='normalized_coefficient' and r['outcome']=='gate')

T=[]
T.append(r'''\documentclass[10pt]{article}
\usepackage[margin=0.78in]{geometry}
\usepackage[T1]{fontenc}\usepackage{lmodern}\usepackage{microtype}
\usepackage{graphicx,booktabs,longtable,tabularx,array,ragged2e,pdflscape,float,caption,subcaption,xcolor,amsmath,enumitem,fancyhdr}
\usepackage[hidelinks]{hyperref}\usepackage[nameinlink,noabbrev]{cleveref}
\definecolor{navy}{HTML}{17365D}\definecolor{lightblue}{HTML}{EAF2F8}\definecolor{muted}{HTML}{536878}
\hypersetup{colorlinks=true,linkcolor=navy,urlcolor=navy,pdftitle={Learned Edge Gates in GATED GLUE}}
\captionsetup{font=small,labelfont=bf,justification=centering}
\setlist{nosep,leftmargin=1.5em}\setlength{\parskip}{4pt}\setlength{\parindent}{0pt}
\pagestyle{fancy}\fancyhf{}\lhead{GATED GLUE edge-gate analysis}\rhead{10x Multiome PBMC}\cfoot{\thepage}
\newcommand{\key}[1]{\colorbox{lightblue}{\parbox{0.96\linewidth}{#1}}}
\newcolumntype{Y}{>{\RaggedRight\arraybackslash}X}
\title{\color{navy}\textbf{Learned Edge Gates in GATED GLUE}\\[0.25em]\Large Extraction, Stability, and Interpretation}
\author{10x Multiome PBMC matched benchmark}
\date{Post hoc analysis of completed runs\\10 August 2026}
\begin{document}\maketitle
\begin{abstract}
This report characterizes the learned global multipliers on directed prior-graph edges in the completed GATED GLUE benchmark. The full-data model is the primary object of interpretation; nine 250-, 2,000-, and 8,000-cell subsample runs quantify sampling stability. All results are descriptive post hoc analyses of saved outputs. No model was retrained and no embeddings or gates were recomputed.
\end{abstract}
\tableofcontents\clearpage
''')

T.append(r'''\section{Executive summary}
For each trainable directed non-self-loop edge, GATED learns a global retention multiplier $g_e=\sigma(a_e)$. It multiplies, but neither renormalizes nor changes the sign of, the original GLUE normalized coefficient. The matched initialization $g_e=0.95$ therefore begins every trainable edge at about 95\% of its original normalized contribution; self-loops remain fixed at one.
''')
T.append(f"""The graph contains \\textbf{{{int(full['n_trainable_edges']):,} trainable directed gates}}. In the full-data reference, the mean gate is {f(full['gate_mean'])}, the median is {f(full['gate_median'])}, and the range is {f(full['gate_min'])}--{f(full['gate_max'])}. Thus the median decreased by only {f(.95-float(full['gate_median']))} from initialization, while a long lower tail contains strongly attenuated edges: {full['n_gate_lt_0.50']} ({pct(full['n_gate_lt_0.50'])}) lie below 0.50 and {full['n_gate_lt_0.10']} ({pct(full['n_gate_lt_0.10'])}) below 0.10. These cutoffs are descriptive, not pruning rules.

Across subsample seeds, Spearman rank reproducibility rises from a mean $\\rho={meanrho[250]:.3f}$ at 250 cells to {meanrho[2000]:.3f} at 2,000 and {meanrho[8000]:.3f} at 8,000. The leading robust suppressions are directed gene-to-region edges headed by {esc(robust[0]['source'])}$\\rightarrow${esc(robust[0]['target'])}, {esc(robust[1]['source'])}$\\rightarrow${esc(robust[1]['target'])}, and {esc(robust[2]['source'])}$\\rightarrow${esc(robust[2]['target'])}. Consistency makes these stronger candidates for follow-up than a one-run extreme, but does not establish biological invalidity.

Only positive prior signs occur in this dataset, so a positive-versus-negative comparison is impossible. Gene-to-region gates have an observed higher mean ({f(groups[1]['mean_gate'])}) than region-to-gene gates ({f(groups[2]['mean_gate'])}); no inferential test accompanies this difference. Raw prior weights are constant (1.0), so their correlations are undefined. The normalized coefficient used in propagation is positively associated with gate ($\\rho={f(normgate['spearman_rho'])}$). The most suppressed edges also dominate the largest absolute attenuations here because their normalized coefficients are large, but the report retains the conceptual distinction.

\\key{{\\textbf{{Interpretation boundary.}} A gate is not an existence probability, confidence score, $p$-value, causal effect, or cell-specific attention. Gates are jointly learned, global, bounded retention terms; model-seed replication and external biological validation remain necessary.}}
""")

T.append(r'''\section{GATED mathematics}
For a directed edge $e=i\rightarrow j$,
\begin{equation}g_e=\operatorname{sigmoid}(a_e),\qquad
m_j=\sum_{e:i\rightarrow j}s_e\,n_e\,g_e\,h_i .\end{equation}
Here $s_e$ is the fixed prior sign, $n_e$ is the original GLUE normalized edge coefficient, $g_e$ is the learned global edge-retention multiplier, and $h_i$ is the source representation. In the matched benchmark, \texttt{gate\_init=0.95}; every trainable non-self-loop edge therefore begins at approximately 95\% of its original normalized contribution. Self-loops use $g=1$ and are fixed/non-trainable. There is \textbf{no post-gate renormalization}. With \texttt{lam\_keep=0}, the gates are learned through the original GLUE objective without explicit retention regularization.

\section{Interpretation rules}
Near one, a gate retains almost all of the original normalized edge contribution; near zero, it strongly attenuates that contribution. Because $0<g_e<1$, a gate cannot amplify above the original normalized magnitude or reverse the fixed sign. It is a \emph{global} multiplier shared across cells, not a probability that an edge exists or a biological relationship is true, not a $p$-value or statistical confidence, not a causal effect, and not cell-specific attention. ``Strongly attenuated'' is the appropriate term; ``false edge'' would require independent validation.

\section{Models analyzed}
The full-data GATED reference is the primary model for interpretation. The nine subsample models assess sampling robustness; they are not averaged into the full-data estimate. All runs use model random seed 0, while the listed subsample seed changes the sampled cells.
''')
model_main=[[esc(r['label']),esc(r['size']),('--' if not r['seed'] else str(int(float(r['seed'])))),'Primary interpretation' if r['label']=='full_reference' else 'Stability / robustness'] for r in models]
T.append("\\begin{table}[H]\\centering\\caption{Completed GATED models included in the analysis.}\n"+table(['Model','Cells','Subsample seed','Role'],model_main,'lrrl','\\small')+"\n\\end{table}")

T.append(r'''\section{Overall gate distribution}
The full-data distribution is concentrated near initialization but is not symmetric: most values remain high while a lower tail reaches 0.022. There is a small, clearly heavily attenuated subset rather than wholesale graph suppression. Across sample sizes the central tendency changes modestly relative to the pronounced gain in rank stability; individual subsample means range from 0.930 to 0.939.
''')
main_dist=[]
for r in dist:
    main_dist.append([esc(r['model']),f(r['gate_mean']),f(r['gate_median']),f(r['gate_sd']),f(r['gate_min']),f(r['gate_q05']),f(r['gate_q95']),f(r['n_gate_lt_0.50'],0),pct(r['n_gate_lt_0.50'])])
T.append("\\begin{table}[H]\\centering\\caption{Gate-distribution overview. All models contain 26,986 trainable gates.}\n"+table(['Model','Mean','Median','SD','Min','Q05','Q95','$n<.50$','\% $<.50$'],main_dist,'lrrrrrrrr')+"\n\\end{table}")
T.append(r'''\begin{figure}[p]\centering
\begin{subfigure}{.49\textwidth}\includegraphics[width=\linewidth]{plots/01_full_gate_histogram.png}\caption{Histogram.}\end{subfigure}\hfill
\begin{subfigure}{.49\textwidth}\includegraphics[width=\linewidth]{plots/02_full_gate_ecdf.png}\caption{Empirical CDF.}\end{subfigure}
\includegraphics[width=.76\linewidth]{plots/03_gate_by_subset_size.png}
\caption{Overall gate distributions. Thresholds shown in the source plots are descriptive only.}\end{figure}
''')

T.append(r'''\section{Lowest gates in the full-data model}
Suppression is $1-g_e$. A gate of 0.05 is therefore approximately 95\% attenuation of the edge's original normalized contribution. The table ranks relative suppression only and excludes self-loops; no entry should be read as a biologically false relationship.
''')
T.append("\\begin{table}[H]\\centering\\caption{Twenty lowest full-reference gates.}\n\\resizebox{\\textwidth}{!}{"+table(['Rank','Source','Target','Type','Sign','Prior $w$','$n_e$','$g_e$','$1-g_e$'],edge_rows(ranked,20,'low'),'rlllrrrrr')+"}\n\\end{table}")
T.append(r'''\begin{figure}[H]\centering\includegraphics[width=.95\linewidth]{plots/08_top20_suppressed_full.png}\caption{Strongest relative suppression in the full-data model.}\end{figure}

\section{Largest message-passing attenuations}
The reduction in original message strength is
\[|n_e|(1-g_e).\]
A tiny gate can have little practical effect when $|n_e|$ was already tiny. Accordingly, three rankings answer different questions: lowest gate is strongest \emph{relative} suppression; largest attenuation is the largest \emph{reduction} in original message strength; and largest absolute effective coefficient is the strongest remaining propagation term.
''')
T.append("\\begin{table}[H]\\centering\\caption{Twenty largest reductions in original normalized message strength.}\n\\resizebox{\\textwidth}{!}{"+table(['Rank','Source','Target','Type','$n_e$','$g_e$','$1-g_e$','Attenuation','Effective'],edge_rows(atten,20,'att'),'rlllrrrrr')+"}\n\\end{table}")
T.append(r'''\begin{figure}[H]\centering\includegraphics[width=.95\linewidth]{plots/09_top20_largest_attenuations.png}\caption{Largest absolute attenuations of original normalized coefficients.}\end{figure}

\section{Strongest remaining edges}
The signed post-gate coefficient is $s_e n_e g_e$; its absolute value ranks the strongest remaining gated propagation. These edges retain near-maximal gates and large original normalized coefficients.
''')
T.append("\\begin{table}[H]\\centering\\caption{Fifteen strongest remaining full-reference coefficients.}\n\\resizebox{\\textwidth}{!}{"+table(['Rank','Source','Target','Type','Sign','$n_e$','$g_e$','Effective','$|$Effective$|$'],edge_rows(effective,15,'eff'),'rlllrrrrr')+"}\n\\end{table}")

T.append(r'''\section{Robustly suppressed edges}
This ranking combines low full-reference and low 8,000-cell cross-seed mean gates. Low gate plus low cross-seed variability is comparatively robust; a low value confined to one seed or accompanied by high variance is unstable and should not be emphasized. Minima and maxima below are the exact three-seed extrema from the aligned 8,000-cell stability table.
''')
robdata=[]
for i,r in enumerate(robust[:20],1):
    s=stability8000[(r['source'],r['target'])]
    robdata.append([i,esc(r['source']),esc(r['target']),esc(r['edge_type']),f(r['gate']),f(r['mean_gate']),f(r['sample_sd_gate']),f(s['min_gate']),f(s['max_gate']),f(s['mean_suppression'])])
T.append("\\begin{table}[H]\\centering\\caption{Top 20 robustly suppressed directed edges (8,000-cell stability basis).}\n\\resizebox{\\textwidth}{!}{"+table(['Rank','Source','Target','Type','Full gate','Seed mean','SD','Min','Max','Mean suppression'],robdata,'rlllrrrrrr')+"}\n\\end{table}")

T.append(r'''\section{Seed stability}
The source file reports pairwise \textbf{Spearman rank correlations}. Reproducibility increases monotonically with sample size: the 250-cell pairs are moderate, the 2,000-cell pairs high, and the 8,000-cell pairs very high. This strongly supports greater ranking stability with more sampled cells. The provided scatter emphasizes mean-versus-SD behavior, but the outputs do not separately quantify correlation within only the low-gate or mid-ranked strata; claims about those strata are therefore withheld.
''')
seeddata=[[r['size'],r['seed_a'],r['seed_b'],f(r['spearman_rho']),('< machine precision' if float(r['p_value'])==0 else f(r['p_value']))] for r in seedcorr]
T.append("\\begin{table}[H]\\centering\\caption{Pairwise seed rank stability.}\n"+table(['Cells','Seed A','Seed B','Spearman $\\rho$','$p$ value'],seeddata,'rrrrr','\\small')+"\n\\end{table}")
T.append(r'''\begin{figure}[H]\centering\includegraphics[width=.88\linewidth]{plots/07_gate_seed_stability.png}\caption{Across-seed mean gate and sample standard deviation by subsample size.}\end{figure}

\section{Edge-type and sign analysis}
Only gene$\rightarrow$region and region$\rightarrow$gene trainable categories exist. Gene$\rightarrow$region has a higher observed mean and median gate, whereas region$\rightarrow$gene has greater mean suppression. Mean coefficient attenuation is nevertheless larger for gene$\rightarrow$region, illustrating that relative gates and absolute message effects differ. Every prior sign is positive; no sign contrast can be estimated. These are descriptive distributions without evidence of biological significance.
''')
grpdata=[[esc(r['grouping']),esc(r['value']),f(r['n'],0),f(r['mean_gate']),f(r['median_gate']),f(r['mean_suppression']),f(r['mean_attenuation'])] for r in groups]
T.append("\\begin{table}[H]\\centering\\caption{Full-reference group summaries.}\n"+table(['Grouping','Value','$n$','Mean gate','Median','Mean suppression','Mean attenuation'],grpdata,'llrrrrr','\\small')+"\n\\end{table}")
T.append(r'''\begin{figure}[H]\centering\includegraphics[width=.76\linewidth]{plots/04_gate_by_edge_type.png}\caption{Observed gate distributions by directed edge type.}\end{figure}

\section{Relation to prior edge strength}
Raw prior weight and normalized propagation coefficient must be distinguished. All raw prior weights equal 1.0, so rank correlations with prior weight are undefined (reported as missing in the authoritative CSV); the data cannot answer whether weak raw-prior edges are more suppressed. By contrast, the normalized coefficient actually used in propagation has Spearman $\rho=0.685$ with gate, $-0.685$ with suppression, and $0.384$ with absolute attenuation (all numerical $p$ values stored as 0.0). Thus larger normalized coefficients tend to be retained more, while their scale can still produce larger absolute reductions. These associations are descriptive and non-causal.
''')
T.append(r'''\begin{figure}[p]\centering
\begin{subfigure}{.49\textwidth}\includegraphics[width=\linewidth]{plots/05_gate_vs_prior_weight.png}\caption{Raw prior weight (constant).}\end{subfigure}\hfill
\begin{subfigure}{.49\textwidth}\includegraphics[width=\linewidth]{plots/06_gate_vs_normalized_coefficient.png}\caption{Normalized coefficient.}\end{subfigure}
\caption{Gate relationships with raw and normalized prior-graph quantities.}\end{figure}

\section{Directional asymmetry}
When both directions exist, $A\rightarrow B$ and $B\rightarrow A$ are independent trainable edges and must not be collapsed. The largest observed difference is 0.931, and all top 15 exceed 0.846, showing substantial direction-specific retention among the most asymmetric pairs. This ranking is descriptive; it does not imply directional biological causality.
''')
asymdata=[[i,esc(r['source']),esc(r['target']),f(r['gate_A_to_B']),f(r['gate_B_to_A']),f(r['absolute_gate_difference'])] for i,r in enumerate(asym[:20],1)]
T.append("\\begin{table}[H]\\centering\\caption{Twenty most asymmetric bidirectional full-reference pairs.}\n\\resizebox{\\textwidth}{!}{"+table(['Rank','$A$','$B$','$g_{A\\to B}$','$g_{B\\to A}$','$|\\Delta g|$'],asymdata,'rllrrr')+"}\n\\end{table}")
T.append(r'''\begin{figure}[H]\centering\includegraphics[width=.95\linewidth]{plots/10_directional_asymmetry.png}\caption{Largest directional gate asymmetries; directions remain separate.}\end{figure}

\section{Sample-size effect}
The mean gate differs only modestly across 250, 2,000, 8,000, and full-data runs, and every distribution retains a high center plus lower tail. Small runs have SDs around 0.078--0.080, while 2,000-cell runs are around 0.067--0.070; 8,000-cell SD varies more (0.068--0.080). The clearest sample-size trend is rank reproducibility: mean pairwise Spearman $\rho$ rises from 0.651 to 0.894 to 0.962. More data therefore appears to stabilize edge-gate estimation in these runs, but this observational benchmark comparison is not a formal convergence proof.

\section{Connection to GATED model performance}
The existing small paired benchmark table (not recomputed here) shows strong GATED graph-connectivity values in the sampled runs, while many other integration metrics remain in the broad neighborhood of GCN. The gate distribution offers a possible mechanistic interpretation: the model retains most guidance contributions while strongly attenuating a minority. This pattern is \emph{consistent with}, but does not show that particular gates caused, the benchmark metric differences; all parameters were jointly optimized.

\section{Main findings}
\begin{enumerate}
\item Most directed edges remain near their initial 0.95 retention: the full-data median is 0.948 and the 5th--95th percentile interval is 0.866--0.981.
\item A minority is strongly attenuated: 198 edges (0.73\%) have gates below 0.50, including 15 (0.06\%) below 0.10.
\item Several leading suppressions recur across 8,000-cell seeds with low SD, notably S100A8, CALHM6, LST1, and HERC5 directed toward specific regions.
\item Relative suppression, absolute attenuation, and remaining effective strength are different estimands, even though the top relative and absolute suppression lists overlap strongly here.
\item Gene$\rightarrow$region gates are observed higher on average than region$\rightarrow$gene gates (0.949 versus 0.920); only positive-sign edges exist.
\item Gate rankings become markedly more reproducible as subsample size increases (mean Spearman $\rho$: 0.651, 0.894, 0.962).
\item Raw prior-weight effects cannot be assessed because the weight is constant; normalized coefficients are positively rank-correlated with retention ($\rho=0.685$).
\end{enumerate}

\section{Limitations}
Gates are learned jointly with every other model parameter, and low gates do not establish biological falsity. They are global rather than cell-specific, cannot amplify beyond the original normalized coefficient, and cannot reverse signs. Self-loops are fixed. The matched benchmark uses \texttt{lam\_keep=0}, so no explicit retention penalty was imposed. Only model random seed 0 was used; subsample seeds measure sampling variability and are not independent model-initialization replicates. Correlated metrics, graph features, and gate values do not establish causation. The descriptive cutoffs are not calibrated pruning thresholds. Finally, external biological validation is required before labeling prior edges incorrect.

\section{Next biological validation steps}
Useful follow-up would annotate robustly suppressed peak--gene edges by genomic distance; compare them with enhancer--gene and promoter annotations; examine chromatin-contact and co-accessibility evidence where available; test enrichment of suppression among weak independent prior evidence; and assess whether robustly retained edges recover established regulatory links. These are proposed validations only; no external database query was performed for this report.

\clearpage\appendix
\section{Full model list and exact paths}
The checkpoint, run-information, prior, RNA, and ATAC paths below are identifiers only; no large inputs were loaded while preparing this report.
''')
pathrows=[]
for r in models:
    pathrows += [[f"\\textbf{{{esc(r['label'])}}} model",r"\path{"+r['model']+"}"],["run info",r"\path{"+r['run_info']+"}"],["prior",r"\path{"+r['prior']+"}"],["RNA",r"\path{"+r['rna']+"}"],["ATAC",r"\path{"+r['atac']+"}"]]
T.append("\\footnotesize\n\\begin{longtable}{>{\\RaggedRight}p{.17\\textwidth}p{.77\\textwidth}}\\toprule Item & Exact path \\\\ \\midrule\\endfirsthead\\toprule Item & Exact path \\\\ \\midrule\\endhead\n"+"\n".join(a+" & "+b+r" \\" for a,b in pathrows)+"\n\\bottomrule\\end{longtable}\\normalsize")

T.append(r'''\section{Gate-distribution statistics}
All quantiles and threshold counts below are read directly from \texttt{gate\_distribution\_summary.csv}. Thresholds are descriptive.
''')
dr=[]
for r in dist: dr.append([esc(r['model']),f(r['gate_min']),f(r['gate_mean']),f(r['gate_median']),f(r['gate_max']),f(r['gate_sd']),*[f(r['gate_q'+q]) for q in ('01','05','10','25','50','75','90','95','99')]])
T.append("\\begin{landscape}\n"+table(['Model','Min','Mean','Median','Max','SD','Q01','Q05','Q10','Q25','Q50','Q75','Q90','Q95','Q99'],dr,'l'+'r'*14,'\\scriptsize',True)+"\n\\end{landscape}")
thr=[]
for r in dist: thr.append([esc(r['model'])]+[f(r['n_gate_lt_'+q],0)+" ("+pct(r['n_gate_lt_'+q])+ ")" for q in ('0.95','0.90','0.75','0.50','0.25','0.10')])
T.append(table(['Model','$g<.95$','$g<.90$','$g<.75$','$g<.50$','$g<.25$','$g<.10$'],thr,'lrrrrrr','\\scriptsize',True))

for title,src,kind,headers,align in [
 ('Top 50 lowest full-reference gates',ranked,'low',['Rank','Source','Target','Type','Sign','Prior $w$','$n_e$','$g_e$','$1-g_e$'],'rlllrrrrr'),
 ('Top 50 largest full-reference attenuations',atten,'att',['Rank','Source','Target','Type','$n_e$','$g_e$','$1-g_e$','Atten.','Effective'],'rlllrrrrr'),
 ('Top 50 largest effective coefficients',effective,'eff',['Rank','Source','Target','Type','Sign','$n_e$','$g_e$','Effective','$|$Effective$|$'],'rlllrrrrr')]:
    T.append(f"\\section{{{title}}}\n\\begin{{landscape}}\n"+table(headers,edge_rows(src,50,kind),align,'\\tiny',True)+"\n\\end{landscape}")

T.append(r'''\section{Top robustly suppressed edges}
The complete supplied robust list is reproduced here (50 candidates), ranked as in the authoritative CSV.
''')
robapp=[]
for i,r in enumerate(robust[:50],1):
    s=stability8000[(r['source'],r['target'])]
    robapp.append([i,esc(r['source']),esc(r['target']),esc(r['edge_type']),f(r['gate']),f(r['mean_gate']),f(r['sample_sd_gate']),f(s['min_gate']),f(s['max_gate']),f(s['mean_suppression'])])
T.append("\\begin{landscape}\n"+table(['Rank','Source','Target','Type','Full gate','Seed mean','SD','Min','Max','Mean suppression'],robapp,'rlllrrrrrr','\\tiny',True)+"\n\\end{landscape}")
T.append(r'''\section{Seed rank-correlation results}''')
T.append(table(['Cells','Seed A','Seed B','Spearman $\\rho$','$p$ value'],seeddata,'rrrrr','\\small'))
T.append(r'''\section{Edge-type group summaries}''')
T.append(table(['Grouping','Value','$n$','Mean gate','Median','Mean suppression','Mean attenuation'],grpdata,'llrrrrr','\\small'))
T.append(r'''\section{Top directional asymmetries}''')
T.append(table(['Rank','$A$','$B$','$g_{A\\to B}$','$g_{B\\to A}$','$|\\Delta g|$'],asymdata,'rllrrr','\\scriptsize',True))
T.append(r'''\section{Data provenance and integrity checks}
The report uses the listed authoritative CSVs and all ten supplied plots. Validation confirmed: ranked trainable-edge tables contain no self-loops; all trainable gates are finite and strictly between zero and one; 15,205 self-loop gates per model equal one; source and target labels are populated; primary rankings match their stated sort keys; stability joins align all 26,986 directed source--target identities across seeds; the full model remains separate from subsamples; correlations are transcribed with their source type; and every figure exists and is nonempty. No corrupted input or silent repair was encountered. Complete per-edge outputs remain available in the CSV files and are not reproduced in full.

\end{document}
''')

(D/"gated_edge_analysis_report.tex").write_text("\n".join(T))
print(D/"gated_edge_analysis_report.tex")
