#!/usr/bin/env python
"""Validate benchmark sources and generate the GCN/GAT/GATED LaTeX report."""

from pathlib import Path
import csv
import math
import re
import statistics

import yaml


HERE = Path(__file__).resolve().parent
OLD = Path("/project/6001426/paa40/GlUE_Exp/GLUE/evaluation")
GCN_ROOT = OLD / "results_gcn_h100/raw"
MATCHED_GAT_ROOT = OLD / "results_gat/raw"
BEST_GAT_ROOT = OLD / "results_gat_tuning/screen_v2/graph_0p05/raw"
GATED_ROOT = HERE / "results_gated/raw"
GATED_LONG = HERE / "results_gated/comparison_10x_gcn_vs_gat_vs_gated/metrics_long.csv"
GATED_COLLECTED = HERE / "results/gated_10x_subsample_targets_metrics.csv"
OLD_TEX = OLD / "best_gat_vs_gcn_metrics.tex"
OUTPUT = HERE / "gcn_gat_gated_metric_comparisons.tex"

DATASET = "10x-Multiome-Pbmc10k"
PRIOR = "gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0"
HP = "dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10"
BEST_HP = HP.replace("lam_graph:0.02", "lam_graph:0.05")
SIZES = (250, 2000, 8000)
SEEDS = (0, 1, 2)
METRICS = (
    ("mean_average_precision", "Mean average precision", "higher"),
    ("normalized_mutual_info", "Normalized mutual information", "higher"),
    ("avg_silhouette_width", "Average silhouette width", "higher"),
    ("avg_silhouette_width_batch", "Batch ASW", "higher"),
    ("graph_connectivity", "Graph connectivity", "higher"),
    ("foscttm", "FOSCTTM", "lower"),
    ("neighbor_conservation", "Neighbor conservation", "higher"),
    ("feature_consistency", "Feature consistency", "higher"),
    ("seurat_alignment_score", "Seurat alignment score", "higher"),
    ("time", "Runtime (hours)", "lower"),
)
EXPECTED = {(size, seed) for size in SIZES for seed in SEEDS}


def metric_path(root, size, seed, hp=HP):
    return (root / DATASET / f"subsample_size:{size}-subsample_seed:{seed}" /
            PRIOR / "GLUE" / hp / "seed:0/metrics.yaml")


def load_yaml_runs(root, hp=HP):
    runs = {}
    for size, seed in sorted(EXPECTED):
        path = metric_path(root, size, seed, hp)
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"Missing metric source: {path}")
        runs[size, seed] = yaml.safe_load(path.read_text())
    return runs


def load_gated_long():
    rows = list(csv.DictReader(GATED_LONG.open()))
    gated_rows = [r for r in rows if r["architecture"] == "gated"]
    if len(gated_rows) != len(EXPECTED) * len(METRICS):
        raise RuntimeError(f"Expected 90 GATED metric rows, found {len(gated_rows)}")
    runs = {key: {} for key in EXPECTED}
    for row in gated_rows:
        key = int(row["size"]), int(row["seed"])
        if key not in EXPECTED or row["metric"] in runs[key]:
            raise RuntimeError(f"Unexpected or duplicate GATED row: {row}")
        runs[key][row["metric"]] = float(row["value"])
    return runs


def finite_and_complete(name, runs):
    if set(runs) != EXPECTED:
        raise RuntimeError(f"{name}: run keys differ from expected nine records")
    wanted = {metric for metric, _, _ in METRICS}
    for key, values in runs.items():
        if not wanted <= set(values):
            raise RuntimeError(f"{name} {key}: missing {sorted(wanted - set(values))}")
        for metric in wanted:
            if not math.isfinite(float(values[metric])):
                raise RuntimeError(f"{name} {key} {metric}: non-finite value")


def hours(value, metric):
    value = float(value)
    return value / 3600 if metric == "time" else value


def summary(runs, size, metric):
    values = [hours(runs[size, seed][metric], metric) for seed in SEEDS]
    return statistics.mean(values), statistics.stdev(values)


def best_flags(values, direction):
    rounded = [round(value, 4) for value in values]
    best = max(rounded) if direction == "higher" else min(rounded)
    return [value == best for value in rounded]


def mean_cell(pair, bold):
    value = rf"${pair[0]:.4f} \pm {pair[1]:.4f}$"
    return rf"\textbf{{{value}}}" if bold else value


def seed_cell(value, metric, bold):
    value = f"{hours(value, metric):.4f}"
    return rf"\textbf{{{value}}}" if bold else value


def old_flags(a, b, direction):
    if direction == "higher":
        return a >= b, b >= a
    return a <= b, b <= a


def regression_check_old_report(gcn, matched, best):
    """Require every old generated metric row to occur in the existing report."""
    old = OLD_TEX.read_text()
    for comparison in (matched, best):
        for metric, label, direction in METRICS:
            cells = [label]
            for size in SIZES:
                a, b = summary(gcn, size, metric), summary(comparison, size, metric)
                fa, fb = old_flags(a[0], b[0], direction)
                cells += [mean_cell(a, fa), mean_cell(b, fb)]
            row = " & ".join(cells) + r" \\"
            if row not in old:
                raise RuntimeError(f"Old-report mean/SD regression failed: {row}")
        for seed in SEEDS:
            for metric, label, direction in METRICS:
                cells = [label]
                for size in SIZES:
                    a = float(gcn[size, seed][metric])
                    b = float(comparison[size, seed][metric])
                    fa, fb = old_flags(a, b, direction)
                    cells += [seed_cell(a, metric, fa), seed_cell(b, metric, fb)]
                row = " & ".join(cells) + r" \\"
                if row not in old:
                    raise RuntimeError(f"Old-report seed regression failed: {row}")


def validate_gated_provenance(gated):
    collected = list(csv.DictReader(GATED_COLLECTED.open()))
    if len(collected) != 9:
        raise RuntimeError(f"Expected 9 collected GATED records, found {len(collected)}")
    for row in collected:
        key = int(row["subsample_size"]), int(row["subsample_seed"])
        if key not in EXPECTED or int(row["method_seed"]) != 0:
            raise RuntimeError(f"Unexpected collected GATED record: {row}")
        expected_path = metric_path(Path("results_gated/raw"), *key).as_posix()
        if row["metrics_path"] != expected_path:
            raise RuntimeError(f"Wrong GATED metric target for {key}: {row['metrics_path']}")
        for metric, _, _ in METRICS:
            column = "time_seconds" if metric == "time" else metric
            if float(row[column]) != float(gated[key][metric]):
                raise RuntimeError(f"Collected/long mismatch for {key} {metric}")
        disk_yaml = yaml.safe_load((HERE / row["metrics_path"]).read_text())
        for metric, _, _ in METRICS:
            if float(disk_yaml[metric]) != float(gated[key][metric]):
                raise RuntimeError(f"YAML/long mismatch for {key} {metric}")

    reference_rel = Path("results_gated/raw") / DATASET / "original" / PRIOR / "GLUE" / HP / "seed:0/feature_latent.csv"
    declared = Path((HERE / "gated_10x_reference_target.txt").read_text().strip())
    if declared != reference_rel:
        raise RuntimeError(f"Unexpected declared GATED reference: {declared}")
    reference = HERE / declared
    if not reference.is_file() or reference.is_symlink() or not reference.stat().st_size:
        raise RuntimeError(f"GATED reference is absent, empty, or a symlink: {reference}")
    rules = (HERE / "workflow/rules/utils.smk").read_text()
    if "f\"{wildcards.path}/{wildcards.dataset}/original/" not in rules:
        raise RuntimeError("Feature-consistency rule no longer selects same-path original reference")
    return reference


gcn = load_yaml_runs(GCN_ROOT)
matched_gat = load_yaml_runs(MATCHED_GAT_ROOT)
best_gat = load_yaml_runs(BEST_GAT_ROOT, BEST_HP)
gated = load_gated_long()
for name, runs in (("GCN", gcn), ("matched GAT", matched_gat),
                   ("best GAT", best_gat), ("GATED", gated)):
    finite_and_complete(name, runs)
regression_check_old_report(gcn, matched_gat, best_gat)
reference = validate_gated_provenance(gated)

lines = [
    r"\documentclass[10pt]{article}",
    r"\usepackage[margin=0.6in]{geometry}",
    r"\usepackage{booktabs}",
    r"\usepackage{pdflscape}",
    r"\usepackage{array}",
    r"\usepackage{graphicx}",
    r"\begin{document}", r"\begin{landscape}",
    r"\section*{GCN, GAT, and GATED metric comparisons}",
    (r"\noindent\textbf{Matched GCN, GAT, and GATED:}\par\noindent \texttt{lr=0.002, "
     r"lam\_graph=0.02, lam\_align=0.05, dim=50, alt\_dim=100, "
     r"hidden\_depth=2, hidden\_dim=256, dropout=0.2, neg\_samples=10}."),
    r"\par\smallskip",
    r"\noindent\textbf{Matched GAT additionally uses:} \texttt{gat\_negative\_slope=0.2}.",
    r"\par\smallskip",
    r"\noindent\textbf{GATED additionally uses:} \texttt{gate\_init=0.95, lam\_keep=0.0}.",
    r"\par\smallskip",
    (r"\noindent\textbf{Best GAT (\texttt{graph\_0p05}):} the same matched "
     r"configuration except \texttt{lam\_graph=0.05}. GATED remains the matched, "
     r"untuned \texttt{lam\_graph=0.02} configuration."),
    r"\par\smallskip",
    (r"\noindent Values are mean $\pm$ sample standard deviation over the three "
     r"matched subsample seeds (0--2). Bold indicates the best value within each "
     r"cell size across the architectures shown in that table. Higher is better "
     r"except for FOSCTTM and runtime, for which lower is better."),
]


def append_table(title, methods):
    labels = [label for label, _ in methods]
    ncols = len(methods) * len(SIZES)
    lines.extend([
        r"\vspace{8pt}", rf"\subsection*{{{title}}}", r"\begin{center}",
        r"\small", r"\setlength{\tabcolsep}{4pt}",
        r"\resizebox{\textwidth}{!}{%", rf"\begin{{tabular}}{{@{{}}l*{{{ncols}}}{{r}}@{{}}}}",
        r"\toprule",
        "& " + " & ".join(rf"\multicolumn{{{len(methods)}}}{{c}}{{{size:,} cells}}" for size in SIZES) + r" \\",
        "".join(rf"\cmidrule(lr){{{2+i*len(methods)}-{1+(i+1)*len(methods)}}}" for i in range(len(SIZES))),
        "Metric & " + " & ".join(labels * len(SIZES)) + r" \\", r"\midrule",
    ])
    for metric, label, direction in METRICS:
        cells = [label]
        for size in SIZES:
            summaries = [summary(runs, size, metric) for _, runs in methods]
            flags = best_flags([item[0] for item in summaries], direction)
            cells.extend(mean_cell(value, bold) for value, bold in zip(summaries, flags))
        lines.append(" & ".join(cells) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"\end{center}"])


def append_seed_table(title, seed, methods):
    labels = [label for label, _ in methods]
    ncols = len(methods) * len(SIZES)
    lines.extend([
        r"\clearpage", rf"\subsection*{{{title}: seed {seed}}}",
        (rf"\noindent Exact metric values for matched subsample seed {seed}. "
         r"Bold indicates the best value within each cell size."),
        r"\vspace{8pt}", r"\begin{center}", r"\small", r"\setlength{\tabcolsep}{4pt}",
        r"\resizebox{\textwidth}{!}{%", rf"\begin{{tabular}}{{@{{}}l*{{{ncols}}}{{r}}@{{}}}}",
        r"\toprule",
        "& " + " & ".join(rf"\multicolumn{{{len(methods)}}}{{c}}{{{size:,} cells}}" for size in SIZES) + r" \\",
        "".join(rf"\cmidrule(lr){{{2+i*len(methods)}-{1+(i+1)*len(methods)}}}" for i in range(len(SIZES))),
        "Metric & " + " & ".join(labels * len(SIZES)) + r" \\", r"\midrule",
    ])
    for metric, label, direction in METRICS:
        cells = [label]
        for size in SIZES:
            values = [hours(runs[size, seed][metric], metric) for _, runs in methods]
            flags = best_flags(values, direction)
            cells.extend(seed_cell(value, "not_time", bold) for value, bold in zip(values, flags))
        lines.append(" & ".join(cells) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"\end{center}"])


matched_methods = (("GCN", gcn), ("Matched GAT", matched_gat), ("GATED", gated))
best_methods = (("GCN", gcn), ("Best GAT", best_gat), ("GATED", gated))
append_table("GCN versus matched GAT versus GATED with matched hyperparameters", matched_methods)
for seed in SEEDS:
    append_seed_table("GCN versus matched GAT versus GATED", seed, matched_methods)
lines.append(r"\clearpage")
append_table("GCN versus best GAT versus GATED", best_methods)
for seed in SEEDS:
    append_seed_table("GCN versus best GAT versus GATED", seed, best_methods)
lines.extend([r"\end{landscape}", r"\end{document}", ""])

OUTPUT.write_text("\n".join(lines))
print(f"Validated old report, 9 finite runs per architecture, and GATED reference: {reference}")
for size in SIZES:
    runtime = summary(gated, size, "time")
    print(f"GATED runtime {size}: {runtime[0]:.4f} +/- {runtime[1]:.4f} hours")
print(f"Wrote {OUTPUT}")
