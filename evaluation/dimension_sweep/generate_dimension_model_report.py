#!/usr/bin/env python3
"""Generate the reporting-only dimension/model comparison LaTeX document."""
from pathlib import Path
import csv
from collections import defaultdict

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "stageA_metrics_long.csv"
OUTPUT = HERE / "dimension_model_comparison_tables.tex"
DIMS = [16, 32, 50, 64, 100]
ARCHES = ["gcn", "gat", "gated"]
DISPLAY = {"gcn": "GCN", "gat": "GAT", "gated": "GATED"}
METRICS = [
    ("mean_average_precision", "MAP", "up"),
    ("normalized_mutual_info", "NMI", "up"),
    ("avg_silhouette_width", "ASW", "up"),
    ("avg_silhouette_width_batch", "Batch ASW", "up"),
    ("graph_connectivity", "Graph connectivity", "up"),
    ("foscttm", "FOSCTTM", "down"),
    ("neighbor_conservation", "Neighbor consistency", "up"),
    ("feature_consistency", "Feature consistency", "up"),
    ("seurat_alignment_score", "Seurat alignment", "up"),
    ("runtime", "Runtime (h)", "down"),
]

rows = list(csv.DictReader(SOURCE.open()))
values = defaultdict(dict)
meta = set()
for row in rows:
    key = (row["architecture"], int(row["dimension"]))
    meta.add((key, int(row["size"]), int(row["subsample_seed"]), int(row["model_seed"]), row["result_path"]))
    value = None if row["value"] == "NA" else float(row["value"])
    values[key][row["metric"]] = value
    values[key]["runtime"] = float(row["runtime"])

assert len(rows) == 135 and len(meta) == 15
assert {k for k, *_ in meta} == {(a, d) for a in ARCHES for d in DIMS}
assert all(size == 2000 and ss == 0 and ms == 0 for _, size, ss, ms, _ in meta)
for a in ARCHES:
    for d in DIMS:
        assert set(values[a, d]) == {m[0] for m in METRICS}
        assert (values[a, d]["feature_consistency"] is not None) == (d == 50)


def esc(text):
    return str(text).replace("_", r"\_").replace("%", r"\%")


def winners(candidates, metric, direction):
    valid = [(name, values[name][metric]) for name in candidates if values[name][metric] is not None]
    if not valid:
        return []
    target = (max if direction == "up" else min)(v for _, v in valid)
    return [name for name, value in valid if value == target]


def fmt(value, metric):
    if value is None:
        return r"\textcolor{gray}{NA$^{\dagger}$}"
    if metric == "runtime":
        return f"{value / 3600:.3f}"
    return f"{value:.4f}"


def metric_label(label, direction):
    return esc(label) + (r" $\uparrow$" if direction == "up" else r" $\downarrow$")


def dimension_table(dim):
    out = [r"\begin{table}[H]", r"\centering", r"\small",
           rf"\caption{{Dimension {dim}: direct architecture comparison (2,000 cells; subsample seed 0; model seed 0; $n=1$ per cell).}}",
           rf"\label{{tab:dim{dim}}}", r"\rowcolors{2}{gray!8}{white}",
           r"\begin{tabular}{@{}lrrrl@{}}", r"\toprule",
           "Metric & GCN & GAT & GATED & Best model \\\\", r"\midrule"]
    candidates = [(a, dim) for a in ARCHES]
    for metric, label, direction in METRICS:
        win = winners(candidates, metric, direction)
        cells = []
        for a in ARCHES:
            text = fmt(values[a, dim][metric], metric)
            if (a, dim) in win:
                text = r"\textbf{" + text + "}"
            cells.append(text)
        best = ", ".join(DISPLAY[a] for a, _ in win) if win else "NA"
        out.append(f"{metric_label(label, direction)} & " + " & ".join(cells) + f" & {best} " + r"\\")
    out += [r"\bottomrule", r"\end{tabular}",
            r"\begin{minipage}{0.92\linewidth}\footnotesize\vspace{2pt}"
            r"$^{\dagger}$NA --- dimension-matched full-data reference unavailable. "
            r"Runtime is training runtime from the benchmark run metadata and is an efficiency measure, not a biological-quality metric."
            r"\end{minipage}", r"\end{table}"]
    return "\n".join(out)


def cross_table(arch):
    out = [r"\begin{table}[H]", r"\centering", r"\scriptsize",
           rf"\caption{{{DISPLAY[arch]} across embedding dimensions (single-run Stage-A results).}}",
           r"\rowcolors{2}{gray!8}{white}", r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
           "Metric & 16 & 32 & 50 & 64 & 100 \\\\", r"\midrule"]
    for metric, label, direction in METRICS:
        candidates = [(arch, d) for d in DIMS]
        win = winners(candidates, metric, direction)
        cells = []
        for d in DIMS:
            text = fmt(values[arch, d][metric], metric)
            if (arch, d) in win:
                text = r"\textbf{" + text + "}"
            cells.append(text)
        out.append(f"{metric_label(label, direction)} & " + " & ".join(cells) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(out)


def best_arch_table():
    chosen = [METRICS[i] for i in (0, 1, 2, 4, 5, 6, 7, 9)]
    heads = ["Dimension"] + [x[1].replace("Neighbor consistency", "Neighbor consist.").replace("Graph connectivity", "Graph conn.").replace("Feature consistency", "Feature consist.").replace("Runtime (h)", "Fastest") for x in chosen]
    out = [r"\begin{landscape}", r"\begin{table}[H]", r"\centering", r"\scriptsize",
           r"\caption{Best observed architecture at each dimension. Runtime identifies the fastest run.}",
           r"\rowcolors{2}{gray!8}{white}", r"\begin{tabular}{@{}rllllllll@{}}", r"\toprule",
           " & ".join(esc(x) for x in heads) + " \\\\", r"\midrule"]
    for d in DIMS:
        cells = [str(d)]
        for metric, _, direction in chosen:
            win = winners([(a, d) for a in ARCHES], metric, direction)
            cells.append("/".join(DISPLAY[a] for a, _ in win) if win else "NA")
        out.append(" & ".join(cells) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}", r"\end{table}", r"\end{landscape}"]
    return "\n".join(out)


def best_dim_table():
    out = [r"\begin{table}[H]", r"\centering", r"\small",
           r"\caption{Best observed dimension within each architecture (descriptive; no composite score).}",
           r"\rowcolors{2}{gray!8}{white}", r"\begin{tabular}{@{}lrrr@{}}", r"\toprule",
           "Metric & GCN best dim & GAT best dim & GATED best dim \\\\", r"\midrule"]
    for metric, label, direction in METRICS:
        cells = []
        for a in ARCHES:
            win = winners([(a, d) for d in DIMS], metric, direction)
            cells.append("/".join(str(d) for _, d in win) if win else "NA")
        out.append(f"{metric_label(label, direction)} & " + " & ".join(cells) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(out)


def baseline_text():
    parts = []
    for a in ARCHES:
        base = values[a, 50]
        smaller_map = max(values[a, 16]["mean_average_precision"], values[a, 32]["mean_average_precision"])
        larger_map = max(values[a, 64]["mean_average_precision"], values[a, 100]["mean_average_precision"])
        parts.append(
            rf"\textbf{{{DISPLAY[a]}.}} At dimension 50, MAP={base['mean_average_precision']:.4f}, "
            rf"NMI={base['normalized_mutual_info']:.4f}, and runtime={base['runtime']/3600:.3f} h. "
            rf"The best smaller-dimension MAP is {smaller_map:.4f}; the best larger-dimension MAP is {larger_map:.4f}."
        )
    return "\n\n".join(parts)


tex = r"""\documentclass[10pt]{article}
\usepackage[margin=0.7in]{geometry}
\usepackage{booktabs,array,float,pdflscape,hyperref,microtype}
\usepackage[table]{xcolor}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\hypersetup{colorlinks=true,linkcolor=blue!50!black,urlcolor=blue!50!black}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\renewcommand{\arraystretch}{1.12}
\pagestyle{plain}
\title{\textbf{GCN vs GAT vs GATED GLUE Across Latent Embedding Dimensions}\\[5pt]
\large 10x Multiome PBMC dimension-sensitivity comparison}
\author{Dimension-sweep reporting summary}
\date{12 August 2026}
\begin{document}
\maketitle
\tableofcontents
\newpage
\section{Executive summary}
This report compares GCN, GAT, and GATED GLUE at embedding dimensions 16, 32, 50, 64, and 100. The currently complete metric set contains only the 2,000-cell Stage-A screen, with subsample seed 0 and model seed 0: every displayed numeric cell therefore represents one run ($n=1$), not a mean across replicates. MAP, NMI, ASW, Batch ASW, graph connectivity, FOSCTTM, neighbor consistency, Seurat alignment, and runtime are available for all 15 configurations. Feature Consistency is valid only at dimension 50, where architecture- and dimension-matched full-data references exist; it is not imputed elsewhere. No globally optimal dimension is asserted.

Arrows indicate direction of preference: $\uparrow$ higher is better and $\downarrow$ lower is better. Runtime is discussed strictly as computational efficiency.

\section{Architecture comparison at each embedding dimension}
"""
tex += "\n".join(rf"\subsection{{Dimension {d}}}" + "\n" + dimension_table(d) for d in DIMS)
tex += r"""
\section{Cross-dimension summary by model}
Bold values are the best observed within an architecture for that row. They are descriptive and do not form a weighted score.
"""
tex += "\n".join(cross_table(a) for a in ARCHES)
tex += "\n\\section{Best architecture at each dimension}\n" + best_arch_table()
tex += "\n\\section{Best dimension within each architecture}\n" + best_dim_table()
tex += r"""
\section{Dimension 50 baseline comparison}
Dimension 50 is the original GLUE default and the only dimension with valid Feature Consistency in the current results.
""" + baseline_text()
tex += r"""
\section{Main observations}
\begin{itemize}
\item No architecture improves monotonically on every biological metric as dimension increases. Different rows favor different dimensions, so the results describe trade-offs rather than a single optimum.
\item For GCN, MAP and NMI peak at dimension 64, while ASW is highest at dimension 16 and neighbor consistency is highest at dimension 100.
\item For GAT, dimension 100 has the highest MAP, Batch ASW, graph connectivity, and neighbor consistency; dimension 32 has the lowest FOSCTTM, while dimension 16 has the highest ASW.
\item For GATED, dimension 64 has the highest MAP, NMI, Batch ASW, and graph connectivity; dimension 32 has the lowest FOSCTTM, while dimension 16 has the highest ASW.
\item Training runtime is not monotonic in embedding dimension in these single runs. GAT is substantially slower than GCN and GATED under the matched settings; this is an observed efficiency difference, not a biological-quality result.
\item Feature Consistency cannot yet support cross-dimension conclusions because only dimension 50 has valid dimension-matched references.
\end{itemize}

\section{Limitations}
\begin{itemize}
\item These are single-run Stage-A screening values at 2,000 cells (subsample seed 0, model seed 0); no sample SD can be estimated.
\item Subsample-seed variation, if later added, would measure data-subset variation and is not equivalent to model-initialization variation.
\item Feature Consistency is unavailable at dimensions 16, 32, 64, and 100 because architecture- and dimension-matched full-data references were not computed. Dimension-50 references were never reused for other dimensions.
\item The best dimension can depend on dataset, preprocessing, and hyperparameters. This report uses matched architecture settings, not independently retuned settings for every dimension.
\item Results at 250 and 8,000 cells are not included because no completed metric summaries currently exist for those size--dimension configurations. Completed model outputs alone were not treated as metric results.
\end{itemize}

\section{Data provenance and validation}
The sole tabular source is \texttt{evaluation/dimension\_sweep/stageA\_metrics\_long.csv}, which is the most complete currently valid dimension-sweep metric source. It contains 135 records: nine metric records for each of 15 unique architecture--dimension configurations. Runtime is repeated consistently in those records and originates from the benchmark run metadata. The associated manifest records the successful replacement metric array as COMPLETED with exit code 0:0 for all required non-default-dimension tasks; failed job records were not included.

Validation confirmed architecture, dimension, sample size, subsample seed, and model seed labels; exactly one configuration per architecture--dimension pair; no duplicate averaging; no failed configurations; lower-is-better handling for FOSCTTM and runtime; higher-is-better handling for the remaining metrics; and no silent filling of missing values. Dimension-50 values originate from validated existing benchmark outputs referenced by the source CSV; other dimensions originate from the repaired, successful Stage-A metric collection. No metric was recomputed for this report.

\vfill
\footnotesize Generated from existing validated metrics only. No training or scheduler submission was performed.
\end{document}
"""
OUTPUT.write_text(tex)
print(f"Wrote {OUTPUT}")
