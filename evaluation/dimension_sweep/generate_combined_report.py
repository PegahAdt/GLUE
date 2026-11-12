#!/usr/bin/env python3
"""Generate the combined 2,000/8,000-cell dimension-sensitivity report."""
from pathlib import Path
from collections import defaultdict
import csv, math
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "metrics_2000_8000_combined.csv"
OUT = HERE / "dimension_model_comparison_2000_8000.tex"
PLOTS = HERE / "plots_2000_8000"
PLOTS.mkdir(exist_ok=True)
DIMS = [16, 32, 50, 64, 100]
SIZES = [2000, 8000]
ARCHES = ["gcn", "gat", "gated"]
NAME = {"gcn":"GCN", "gat":"GAT", "gated":"GATED"}
METRICS = [
 ("mean_average_precision","MAP","up"), ("normalized_mutual_info","NMI","up"),
 ("avg_silhouette_width","ASW","up"), ("avg_silhouette_width_batch","Batch ASW","up"),
 ("graph_connectivity","Graph connectivity","up"), ("foscttm","FOSCTTM","down"),
 ("neighbor_conservation","Neighbor consistency","up"),
 ("feature_consistency","Feature consistency","up"),
 ("seurat_alignment_score","Seurat alignment","up"), ("runtime","Runtime","down")]
LABEL = {m:l for m,l,_ in METRICS}; DIRECTION = {m:d for m,_,d in METRICS}

rows = list(csv.DictReader(SOURCE.open()))
v = defaultdict(dict); paths = {}
for r in rows:
    key=(r["architecture"],int(r["dim"]),int(r["size"])); paths[key]=r["result_path"]
    v[key][r["metric"]] = None if r["value"] == "NA" else float(r["value"])
    v[key]["runtime"] = float(r["runtime"])
assert len(rows)==270 and len(paths)==30
assert set(paths)=={(a,d,s) for a in ARCHES for d in DIMS for s in SIZES}
assert all((v[a,d,s]["feature_consistency"] is not None)==(d==50) for a,d,s in paths)

def esc(x): return str(x).replace("_",r"\_").replace("%",r"\%").replace("&",r"\&")
def fmt(x,m,change=False):
    if x is None: return r"\textcolor{gray}{NA$^{\dagger}$}"
    if m=="runtime": return f"{x/3600:.3f}" if not change else f"{x:.2f}$\times$"
    return f"{x:+.4f}" if change else f"{x:.4f}"
def arrow(m): return r" $\uparrow$" if DIRECTION[m]=="up" else r" $\downarrow$"
def wins(keys,m):
    q=[(k,v[k][m]) for k in keys if v[k][m] is not None]
    if not q:return []
    target=(max if DIRECTION[m]=="up" else min)(x for _,x in q)
    return [k for k,x in q if abs(x-target)<1e-12]

# Two-panel metric plots; missing feature consistency is intentionally not plotted.
colors={"gcn":"#2864a8","gat":"#d97904","gated":"#238b45"}; marks={"gcn":"o","gat":"s","gated":"^"}
for m,l,_ in METRICS:
    if m in ("feature_consistency",): continue
    fig,axs=plt.subplots(1,2,figsize=(9.2,3.25),sharey=False)
    for ax,s in zip(axs,SIZES):
        for a in ARCHES:
            ys=[v[a,d,s][m]/3600 if m=="runtime" else v[a,d,s][m] for d in DIMS]
            ax.plot(DIMS,ys,color=colors[a],marker=marks[a],linewidth=2,label=NAME[a])
        ax.set_title(f"{s:,} cells"); ax.set_xticks(DIMS); ax.grid(alpha=.25); ax.set_xlabel("Latent dimension")
        ax.set_ylabel("Runtime (hours)" if m=="runtime" else l)
    axs[1].legend(frameon=False,ncol=3,loc="best")
    fig.suptitle(f"{l} across embedding dimensions",fontweight="bold"); fig.tight_layout()
    fig.savefig(PLOTS/f"{m}.pdf",bbox_inches="tight"); plt.close(fig)

def architecture_table(d,s):
    z=[r"\begin{table}[H]\centering\small",f"\\caption{{Dimension {d}, {s:,} cells (subsample seed 0; model seed 0; $n=1$).}}",
       r"\rowcolors{2}{gray!8}{white}\begin{tabular}{@{}lrrrl@{}}\toprule",r"Metric & GCN & GAT & GATED & Best model \\\midrule"]
    keys=[(a,d,s) for a in ARCHES]
    for m,l,_ in METRICS:
        w=wins(keys,m); cells=[]
        for a in ARCHES:
            x=fmt(v[a,d,s][m],m)
            if (a,d,s) in w:x=r"\textbf{"+x+"}"
            cells.append(x)
        best="/".join(NAME[k[0]] for k in w) if w else "NA"
        z.append(f"{esc(l)}{arrow(m)} & "+" & ".join(cells)+f" & {best} \\\\")
    z += [r"\bottomrule\end{tabular}",r"\end{table}"]
    return "\n".join(z)

def size_change_table(a):
    z=[r"\begin{landscape}\begin{longtable}{@{}llrrr@{}}",f"\\caption{{{NAME[a]}: matched 2,000- versus 8,000-cell observations.}}\\\\",
       r"\toprule Metric & Dim & 2,000 & 8,000 & Change \\\midrule\endfirsthead",
       r"\toprule Metric & Dim & 2,000 & 8,000 & Change \\\midrule\endhead"]
    for m,l,_ in METRICS:
        for d in DIMS:
            x,y=v[a,d,2000][m],v[a,d,8000][m]
            ch=None if x is None or y is None else (y/x if m=="runtime" else y-x)
            z.append(f"{esc(l)}{arrow(m)} & {d} & {fmt(x,m)} & {fmt(y,m)} & {fmt(ch,m,True)} \\\\")
        z.append(r"\addlinespace")
    z += [r"\bottomrule\end{longtable}\end{landscape}"]
    return "\n".join(z)

def cross_table(a,s):
    z=[r"\begin{table}[H]\centering\scriptsize",f"\\caption{{{NAME[a]} across dimensions at {s:,} cells.}}",
       r"\rowcolors{2}{gray!8}{white}\begin{tabular}{@{}lrrrrr@{}}\toprule",r"Metric & 16 & 32 & 50 & 64 & 100 \\\midrule"]
    for m,l,_ in METRICS:
        w=wins([(a,d,s) for d in DIMS],m); cells=[]
        for d in DIMS:
            x=fmt(v[a,d,s][m],m)
            if (a,d,s) in w and m!="feature_consistency":x=r"\textbf{"+x+"}"
            cells.append(x)
        z.append(f"{esc(l)}{arrow(m)} & "+" & ".join(cells)+" \\\\")
    z += [r"\bottomrule\end{tabular}\end{table}"]
    return "\n".join(z)

def best_arch_table():
    z=[r"\begin{landscape}\begin{table}[H]\centering\scriptsize",r"\caption{Best observed architecture by metric, cell count, and dimension.}",
       r"\begin{tabular}{@{}rrlllllllllll@{}}\toprule",r"Cells & Dim & MAP & NMI & ASW & Batch ASW & Graph Conn. & FOSCTTM & Neighbor & Feature & Seurat & Fastest \\\midrule"]
    for s in SIZES:
      for d in DIMS:
        cells=[f"{s:,}",str(d)]
        for m,_,_ in METRICS:
            w=wins([(a,d,s) for a in ARCHES],m); cells.append("/".join(NAME[k[0]] for k in w) if w else "NA")
        z.append(" & ".join(cells)+" \\\\")
      z.append(r"\addlinespace")
    z += [r"\bottomrule\end{tabular}\end{table}\end{landscape}"]
    return "\n".join(z)

def best_dim_table(s):
    z=[r"\begin{table}[H]\centering\small",f"\\caption{{Best observed dimension within each model at {s:,} cells.}}",
       r"\begin{tabular}{@{}lrrr@{}}\toprule",r"Metric & GCN best dim & GAT best dim & GATED best dim \\\midrule"]
    for m,l,_ in METRICS:
        cells=[]
        for a in ARCHES:
            if m=="feature_consistency": cells.append(r"\multicolumn{1}{c}{not comparable}")
            else:
                w=wins([(a,d,s) for d in DIMS],m); cells.append("/".join(str(k[1]) for k in w))
        z.append(f"{esc(l)}{arrow(m)} & "+" & ".join(cells)+" \\\\")
    z += [r"\bottomrule\end{tabular}\end{table}"]
    return "\n".join(z)

# Existing replicated benchmark is dimension 50 only (subsample seeds 0--2).
rep_source=HERE.parent/"results_gated/comparison_10x_gcn_vs_gat_vs_gated/metrics_long.csv"
rep=defaultdict(list)
if rep_source.is_file():
  for r in csv.DictReader(rep_source.open()):
    if int(r["size"])==8000 and int(r["seed"]) in (0,1,2): rep[(r["architecture"],r["metric"])].append(float(r["value"]))
def replicated_table():
    z=[r"\begin{table}[H]\centering\scriptsize",r"\caption{Existing replicated 8,000-cell dimension-50 benchmark (mean $\pm$ SD across subsample seeds 0--2; model seed 0).}",
       r"\begin{tabular}{@{}lrrr@{}}\toprule Metric & GCN & GAT & GATED \\\midrule"]
    for m,l,_ in METRICS:
        old="time" if m=="runtime" else m; cells=[]
        for a in ARCHES:
            q=rep.get((a,old),[])
            if len(q)==3:
                mean,sd=np.mean(q),np.std(q,ddof=1)
                cells.append(f"{mean/3600:.3f} $\\pm$ {sd/3600:.3f}" if m=="runtime" else f"{mean:.4f} $\\pm$ {sd:.4f}")
            else: cells.append("NA")
        z.append(f"{esc(l)}{arrow(m)} & "+" & ".join(cells)+" \\\\")
    z += [r"\bottomrule\end{tabular}\end{table}"]
    return "\n".join(z)

# Concise data-derived descriptors.
def bestdims(a,s,m): return [k[1] for k in wins([(a,d,s) for d in DIMS],m)]
plateau=[]
for a in ARCHES:
    base=v[a,50,8000]["mean_average_precision"]
    later=max(v[a,d,8000]["mean_average_precision"] for d in (64,100))
    plateau.append(f"{NAME[a]} {later-base:+.4f}")

tex=r"""\documentclass[10pt]{article}
\usepackage[margin=0.68in]{geometry}
\usepackage{booktabs,array,float,longtable,pdflscape,graphicx,hyperref,microtype}
\usepackage[table]{xcolor}\usepackage[T1]{fontenc}\usepackage{lmodern}
\hypersetup{colorlinks=true,linkcolor=blue!45!black,urlcolor=blue!45!black}
\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}\renewcommand{\arraystretch}{1.10}
\title{\textbf{GCN vs GAT vs GATED GLUE Across Latent Embedding Dimensions}\\[5pt]
\large Comparison at 2,000 and 8,000 cells --- 10x Multiome PBMC}
\author{Dimension-sweep reporting summary}\date{12 August 2026}
\begin{document}\maketitle\tableofcontents\newpage
\section{Executive summary}
GCN, GAT, and GATED GLUE are compared at latent dimensions 16, 32, 50, 64, and 100 using 2,000 and 8,000 cells. The primary comparison is exactly matched on subsample seed 0 and model seed 0; every primary value is therefore one observed run ($n=1$). Existing 8,000-cell dimension-50 results across subsample seeds 0--2 are retained in a separate mean $\pm$ SD table and are never mixed into the matched primary tables.

MAP, NMI, ASW, Batch ASW, graph connectivity, FOSCTTM, neighbor consistency, Seurat alignment, and runtime are available for all 30 primary configurations. Feature Consistency is available only at dimension 50 because no dimension-matched full-data references exist for dimensions 16, 32, 64, or 100. Missing values are shown explicitly. FOSCTTM and runtime are lower-is-better; runtime is an efficiency measure, not a biological-quality metric. With single-run primary results, this report uses ``best observed'' wording and does not claim an optimal dimension or statistical significance.

\section{Core architecture tables by dimension}
Bold values identify the best valid architecture within a row. $^{\dagger}$NA means a dimension-matched Feature Consistency reference is unavailable.
"""
for d in DIMS:
    tex += f"\\subsection{{Dimension {d}}}\n"+architecture_table(d,2000)+"\n"+architecture_table(d,8000)+"\n"
tex += "\\section{Matched cell-count comparisons by architecture}\nChanges are $8{,}000-2{,}000$ for quality metrics. Runtime change is the ratio $t_{8000}/t_{2000}$. FOSCTTM differences remain ordinary signed differences; lower is better. No change is labeled statistically significant.\n"
for a in ARCHES: tex += f"\\subsection{{{NAME[a]}}}\n"+size_change_table(a)+"\n"
for s in SIZES:
    tex += f"\\section{{Cross-dimension tables: {s:,} cells}}\n"
    for a in ARCHES: tex += cross_table(a,s)+"\n"
tex += "\\section{Best observed architecture at each dimension}\n"+best_arch_table()+"\n"
tex += "\\section{Best observed dimension within each model}\n"+best_dim_table(2000)+"\n"+best_dim_table(8000)+"\n"
tex += "\\section{Existing replicated dimension-50 results}\n"+replicated_table()+r"""
\section{Dimension-sensitivity plots}
The panels separate sample sizes to avoid six-line clutter. Lines connect only observed values; Feature Consistency is omitted because one valid dimension cannot define a curve.
"""
plot_metrics=[x for x in METRICS if x[0]!="feature_consistency"]
for i,(m,l,_) in enumerate(plot_metrics):
    tex += r"\begin{figure}[H]\centering\includegraphics[width=.94\linewidth]{"+f"plots_2000_8000/{m}.pdf"+r"}\caption{"+esc(l)+r" versus latent dimension.}\end{figure}"+"\n"
tex += r"""
\section{Scientific interpretation}
\begin{enumerate}
\item \textbf{Does increasing embedding size generally improve performance?} No uniform monotonic improvement is observed. MAP, NMI, mixing, pairing, and neighborhood metrics often favor different dimensions within the same architecture.
\item \textbf{Do improvements plateau?} Several curves flatten or reverse after 50--64 dimensions. This suggests metric-specific plateaus rather than a universal saturation point.
\item \textbf{Does the preferred dimension change with sample size?} Yes for several architecture--metric pairs; the best-observed dimension tables show the exact changes. No single preferred dimension is shared by all metrics at either size.
\item \textbf{Does GAT benefit more from larger dimensions?} The data do not support a blanket claim: some GAT metrics rise at larger dimensions while ASW and FOSCTTM can favor smaller dimensions.
\item \textbf{Is GATED dimension-sensitive?} GATED shows visible but metric-dependent variation. It is neither uniformly insensitive nor uniformly more sensitive than the alternatives.
\item \textbf{Does runtime scale differently?} Yes. GAT remains the slowest architecture in these matched runs, while GCN and GATED are closer. Runtime is not monotonic with dimension because convergence time and scheduler-independent training dynamics vary by run.
\item \textbf{Is default dimension 50 near a plateau?} Dimension 50 lies near a plateau for several curves, but later dimensions still yield best-observed values for some metrics. Relative 8,000-cell MAP change from dimension 50 to the better of 64/100 is: """+esc(", ".join(plateau))+r""". Thus dimension 50 is a defensible baseline, not a demonstrated optimum.
\item \textbf{Are dimensions clearly dominated at both sizes?} No dimension is declared globally dominated because metric directions conflict and no weighting scheme was specified.
\end{enumerate}

\section{Data integrity and limitations}
All 15 2,000-cell and all 15 8,000-cell architecture--dimension combinations are present exactly once in the matched data. The 2,000-cell source is the authoritative Stage-A long table. The 8,000-cell non-default dimensions use only model job 54328002 records with completed exit code 0:0; dimension-50 benchmark outputs were independently validated and reused. Architecture, requested dimension, sample size, subsample/model seeds, latent non-emptiness and shape, scientific hyperparameters, and unique paths were checked before metrics were accepted. Failed metric job 54418992 and every failed/incomplete model record are excluded. No missing result was inferred or filled, sample sizes were never averaged together, and runtime consistently comes from run metadata.

Primary comparisons are single runs and cannot estimate run-to-run uncertainty. The replicated appendix is restricted to the already-existing dimension-50 8,000-cell benchmark and reflects subsample-seed variation, not model-seed variation. Feature Consistency cannot be compared across dimensions. Conclusions are descriptive and specific to this dataset and matched hyperparameters.

\appendix\section{Source paths}
Combined table: \texttt{evaluation/dimension\_sweep/metrics\_2000\_8000\_combined.csv}.\\
Validated 8,000-run inventory: \texttt{evaluation/dimension\_sweep/available\_8000\_runs.csv}.\\
No model training was performed, no GPU job was submitted, and existing experiment outputs were not modified.
\end{document}
"""
OUT.write_text(tex)
print(f"Wrote {OUT} and {len(plot_metrics)} plots")
