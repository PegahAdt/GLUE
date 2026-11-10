from pathlib import Path
import yaml
import pandas as pd
import math

BASE = Path("results/raw/10x-Multiome-Pbmc10k")
PRIOR = "gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0"
HP = "dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10"

# Paper values you asked to include per seed.
# These are the paper-reported GLUE values for 10x-Multiome-Pbmc10k, subsample size 250.
paper = {
    0: {
        "mean_average_precision": 0.704142,
        "avg_silhouette_width": 0.502843,
        "avg_silhouette_width_batch": 0.933007,
        "graph_connectivity": 0.895343,
        "foscttm": 0.202704,
        "neighbor_conservation": 0.132302,
        "feature_consistency": 0.439931,
        "seurat_alignment_score": 1.000000,
    },
    1: {
        "mean_average_precision": 0.715681,
        "avg_silhouette_width": 0.508752,
        "avg_silhouette_width_batch": 0.939989,
        "graph_connectivity": 0.917331,
        "foscttm": 0.200040,
        "neighbor_conservation": 0.154206,
        "feature_consistency": 0.436099,
        "seurat_alignment_score": 1.000000,
    },
    2: {
        "mean_average_precision": 0.705969,
        "avg_silhouette_width": 0.510384,
        "avg_silhouette_width_batch": 0.909712,
        "graph_connectivity": 0.909649,
        "foscttm": 0.215152,
        "neighbor_conservation": 0.138897,
        "feature_consistency": 0.434967,
        "seurat_alignment_score": 1.000000,
    },
    3: {
        "mean_average_precision": 0.735269,
        "avg_silhouette_width": 0.509610,
        "avg_silhouette_width_batch": 0.918902,
        "graph_connectivity": 0.935406,
        "foscttm": 0.225544,
        "neighbor_conservation": 0.137976,
        "feature_consistency": 0.431853,
        "seurat_alignment_score": 1.000000,
    },
    4: {
        "mean_average_precision": 0.722003,
        "avg_silhouette_width": 0.512905,
        "avg_silhouette_width_batch": 0.912311,
        "graph_connectivity": 0.888021,
        "foscttm": 0.213240,
        "neighbor_conservation": 0.153762,
        "feature_consistency": 0.434597,
        "seurat_alignment_score": 1.000000,
    },
    5: {
        "mean_average_precision": 0.713181,
        "avg_silhouette_width": 0.501677,
        "avg_silhouette_width_batch": 0.922478,
        "graph_connectivity": 0.872334,
        "foscttm": 0.215992,
        "neighbor_conservation": 0.136841,
        "feature_consistency": 0.426125,
        "seurat_alignment_score": 1.000000,
    },
    6: {
        "mean_average_precision": 0.693678,
        "avg_silhouette_width": 0.507250,
        "avg_silhouette_width_batch": 0.909738,
        "graph_connectivity": 0.902614,
        "foscttm": 0.203432,
        "neighbor_conservation": 0.146683,
        "feature_consistency": 0.440329,
        "seurat_alignment_score": 1.000000,
    },
    7: {
        "mean_average_precision": 0.656836,
        "avg_silhouette_width": 0.506688,
        "avg_silhouette_width_batch": 0.939717,
        "graph_connectivity": 0.887269,
        "foscttm": 0.219568,
        "neighbor_conservation": 0.134643,
        "feature_consistency": 0.440569,
        "seurat_alignment_score": 1.000000,
    },
}

metrics = [
    ("mean_average_precision", "Mean average precision"),
    ("normalized_mutual_info", "Normalized mutual information"),
    ("avg_silhouette_width", "Average silhouette width"),
    ("avg_silhouette_width_batch", "Average silhouette width batch"),
    ("graph_connectivity", "Graph connectivity"),
    ("foscttm", "FOSCTTM"),
    ("neighbor_conservation", "Neighbor conservation"),
    ("feature_consistency", "Feature consistency"),
    ("seurat_alignment_score", "Seurat alignment score"),
    ("time_hours", "Runtime, hours"),
]

rows = []

for seed in range(8):
    p = (
        BASE
        / f"subsample_size:250-subsample_seed:{seed}"
        / PRIOR
        / "GLUE"
        / HP
        / "seed:0"
        / "metrics.yaml"
    )

    if not p.exists():
        raise FileNotFoundError(f"Missing: {p}")

    with open(p) as f:
        m = yaml.safe_load(f)

    m["time_hours"] = m.get("time", None) / 3600 if m.get("time") is not None else None
    m["subsample_seed"] = seed
    m["n_cells"] = m.get("n_cells")
    rows.append(m)

df = pd.DataFrame(rows)

def fmt(x):
    if x is None:
        return r"\textemdash"
    if isinstance(x, float) and math.isnan(x):
        return r"\textemdash"
    if isinstance(x, int):
        return str(x)
    return f"{float(x):.6f}"

def diff_fmt(my, paper_val):
    if my is None or paper_val is None:
        return r"\textemdash"
    if isinstance(my, float) and math.isnan(my):
        return r"\textemdash"
    return f"{float(my) - float(paper_val):+.6f}"

lines = []

lines.append(r"\documentclass[11pt]{article}")
lines.append(r"\usepackage[margin=0.75in]{geometry}")
lines.append(r"\usepackage{amsmath}")
lines.append(r"\usepackage{booktabs}")
lines.append(r"\usepackage{graphicx}")
lines.append(r"\usepackage{float}")
lines.append(r"\usepackage{caption}")
lines.append(r"\begin{document}")
lines.append("")
lines.append(r"\title{GLUE Reproduction Results: 10x-Multiome-Pbmc10k, Subsample Size 250}")
lines.append(r"\author{}")
lines.append(r"\date{}")
lines.append(r"\maketitle")
lines.append("")
lines.append(r"\section*{Experiment setting}")
lines.append("")
lines.append(r"This document compares reproduced GLUE results against paper-reported GLUE values for the 10x-Multiome-Pbmc10k dataset at subsample size 250. The GLUE model seed is fixed at 0, while the subsample seed varies from 0 to 7.")
lines.append("")
lines.append(r"\section*{Per-seed comparison}")
lines.append("")

for _, row in df.iterrows():
    seed = int(row["subsample_seed"])

    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(rf"\caption{{Paper-reported and reproduced GLUE metrics for subsample seed {seed}.}}")
    lines.append(rf"\label{{tab:glue_seed_{seed}_comparison}}")
    lines.append(r"\resizebox{\textwidth}{!}{")
    lines.append(r"\begin{tabular}{lccc}")
    lines.append(r"\toprule")
    lines.append(r"Metric & Paper GLUE & My GLUE Run & My $-$ Paper \\")
    lines.append(r"\midrule")
    lines.append(rf"Number of cells & \textemdash & {int(row['n_cells'])} & \textemdash \\")

    for key, label in metrics:
        my_val = row.get(key, None)
        paper_val = paper.get(seed, {}).get(key, None)

        lines.append(
            rf"{label} & {fmt(paper_val)} & {fmt(my_val)} & {diff_fmt(my_val, paper_val)} \\"
        )

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"}")
    lines.append(r"\end{table}")
    lines.append("")

lines.append(r"\clearpage")
lines.append(r"\section*{Mean comparison across subsample seeds}")
lines.append("")

lines.append(r"\begin{table}[H]")
lines.append(r"\centering")
lines.append(r"\caption{Mean and standard deviation across subsample seeds 0--7.}")
lines.append(r"\label{tab:glue_10x_250_mean_comparison}")
lines.append(r"\resizebox{\textwidth}{!}{")
lines.append(r"\begin{tabular}{lccc}")
lines.append(r"\toprule")
lines.append(r"Metric & Paper GLUE & My GLUE Run & Difference in Means \\")
lines.append(r"\midrule")

for key, label in metrics:
    my_mean = df[key].mean()
    my_std = df[key].std()

    paper_vals = [paper[s][key] for s in range(8) if key in paper[s]]
    if paper_vals:
        ps = pd.Series(paper_vals)
        paper_mean = ps.mean()
        paper_std = ps.std()
        diff = my_mean - paper_mean
        paper_text = rf"${paper_mean:.4f} \pm {paper_std:.4f}$"
        diff_text = rf"${diff:+.4f}$"
    else:
        paper_text = r"\textemdash"
        diff_text = r"\textemdash"

    my_text = rf"${my_mean:.4f} \pm {my_std:.4f}$"

    lines.append(rf"{label} & {paper_text} & {my_text} & {diff_text} \\")

lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"}")
lines.append(r"\end{table}")
lines.append("")
lines.append(r"\noindent Lower FOSCTTM is better. Higher values are better for the other accuracy or consistency metrics.")
lines.append("")
lines.append(r"\end{document}")

tex = "\n".join(lines)

print(tex)

Path("glue_10x_250_completed_tables.tex").write_text(tex)
print("\n\nWrote glue_10x_250_completed_tables.tex", flush=True)
