"""Generate standalone LaTeX tables comparing GCN with matched and best GAT."""

from pathlib import Path
import re
import statistics

import yaml


ROOT = Path(__file__).resolve().parent
MATCHED_GAT_ROOT = ROOT / "results_gat" / "raw"
BEST_GAT_ROOT = ROOT / "results_gat_tuning" / "screen_v2" / "graph_0p05" / "raw"
GCN_ROOT = ROOT / "results_gcn_h100" / "raw"
OUTPUT = ROOT / "best_gat_vs_gcn_metrics.tex"

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


def load_runs(root):
    runs = {}
    for path in root.glob("**/metrics.yaml"):
        match = re.search(
            r"subsample_size:(\d+)-subsample_seed:(\d+)", path.as_posix()
        )
        if match is None:
            continue
        size, seed = map(int, match.groups())
        if size in SIZES and seed in SEEDS:
            with path.open() as stream:
                runs[size, seed] = yaml.safe_load(stream)
    return runs


def summarize(runs, size, metric):
    values = [float(runs[size, seed][metric]) for seed in SEEDS]
    if metric == "time":
        values = [value / 3600 for value in values]
    return statistics.mean(values), statistics.stdev(values)


def formatted(summary, bold=False):
    mean, std = summary
    value = rf"${mean:.4f} \pm {std:.4f}$"
    return rf"\textbf{{{value}}}" if bold else value


def formatted_single(value, metric, bold=False):
    value = float(value)
    if metric == "time":
        value /= 3600
    text = f"{value:.4f}"
    return rf"\textbf{{{text}}}" if bold else text


gcn = load_runs(GCN_ROOT)
matched_gat = load_runs(MATCHED_GAT_ROOT)
best_gat = load_runs(BEST_GAT_ROOT)
expected = {(size, seed) for size in SIZES for seed in SEEDS}
for name, runs in (("GCN", gcn), ("matched GAT", matched_gat), ("best GAT", best_gat)):
    if set(runs) != expected:
        raise RuntimeError(f"{name} runs incomplete: missing {sorted(expected - set(runs))}")


lines = [
    r"\documentclass[10pt]{article}",
    r"\usepackage[margin=0.6in]{geometry}",
    r"\usepackage{booktabs}",
    r"\usepackage{pdflscape}",
    r"\usepackage{array}",
    r"\begin{document}",
    r"\begin{landscape}",
    r"\section*{GAT and GCN metric comparisons}",
    (
        r"\noindent\textbf{Matched GAT and GCN:} \texttt{lr=0.002, "
        r"lam\_graph=0.02, lam\_align=0.05, dim=50, alt\_dim=100, "
        r"hidden\_depth=2, hidden\_dim=256, dropout=0.2, neg\_samples=10}. "
        r"The GAT additionally uses \texttt{gat\_negative\_slope=0.2}."
    ),
    r"\par\smallskip",
    (
        r"\noindent\textbf{Best GAT (\texttt{graph\_0p05}):} the matched "
        r"configuration with \texttt{lam\_graph=0.05}."
    ),
    r"\par\smallskip",
    (
        r"\noindent Values are mean $\pm$ sample standard deviation over the "
        r"three matched subsample seeds (0--2). Bold indicates the better mean "
        r"within each size; higher is better except for FOSCTTM and runtime."
    ),
]


def append_table(title, comparison_runs, comparison_label):
    lines.extend(
        [
            r"\vspace{8pt}",
            rf"\subsection*{{{title}}}",
            r"\begin{center}",
            r"\small",
            r"\setlength{\tabcolsep}{5pt}",
            r"\begin{tabular}{@{}l*{6}{r}@{}}",
            r"\toprule",
            r"& \multicolumn{2}{c}{250 cells} & \multicolumn{2}{c}{2,000 cells} "
            r"& \multicolumn{2}{c}{8,000 cells} \\",
            r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(l){6-7}",
            f"Metric & GCN & {comparison_label} & GCN & {comparison_label} & "
            f"GCN & {comparison_label} " + r"\\",
            r"\midrule",
        ]
    )
    for metric, label, direction in METRICS:
        cells = [label]
        for size in SIZES:
            gcn_summary = summarize(gcn, size, metric)
            comparison_summary = summarize(comparison_runs, size, metric)
            comparison_better = (
                comparison_summary[0] > gcn_summary[0]
                if direction == "higher"
                else comparison_summary[0] < gcn_summary[0]
            )
            tie = comparison_summary[0] == gcn_summary[0]
            cells.extend(
                (
                    formatted(gcn_summary, bold=(not comparison_better or tie)),
                    formatted(comparison_summary, bold=(comparison_better or tie)),
                )
            )
        lines.append(" & ".join(cells) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{center}"])


def append_seed_table(title, seed, comparison_runs, comparison_label):
    lines.extend(
        [
            r"\clearpage",
            rf"\subsection*{{{title}: seed {seed}}}",
            (
                rf"\noindent Exact metric values for matched subsample seed {seed}. "
                r"Bold indicates the better value within each size."
            ),
            r"\vspace{8pt}",
            r"\begin{center}",
            r"\small",
            r"\setlength{\tabcolsep}{6pt}",
            r"\begin{tabular}{@{}l*{6}{r}@{}}",
            r"\toprule",
            r"& \multicolumn{2}{c}{250 cells} & \multicolumn{2}{c}{2,000 cells} "
            r"& \multicolumn{2}{c}{8,000 cells} \\",
            r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(l){6-7}",
            f"Metric & GCN & {comparison_label} & GCN & {comparison_label} & "
            f"GCN & {comparison_label} " + r"\\",
            r"\midrule",
        ]
    )
    for metric, label, direction in METRICS:
        cells = [label]
        for size in SIZES:
            gcn_value = float(gcn[size, seed][metric])
            comparison_value = float(comparison_runs[size, seed][metric])
            comparison_better = (
                comparison_value > gcn_value
                if direction == "higher"
                else comparison_value < gcn_value
            )
            tie = comparison_value == gcn_value
            cells.extend(
                (
                    formatted_single(
                        gcn_value, metric, bold=(not comparison_better or tie)
                    ),
                    formatted_single(
                        comparison_value,
                        metric,
                        bold=(comparison_better or tie),
                    ),
                )
            )
        lines.append(" & ".join(cells) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{center}"])


append_table(
    "GCN versus GAT with matched hyperparameters", matched_gat, "Matched GAT"
)
for seed in SEEDS:
    append_seed_table(
        "GCN versus GAT with matched hyperparameters",
        seed,
        matched_gat,
        "Matched GAT",
    )
lines.append(r"\clearpage")
append_table("GCN versus best GAT", best_gat, "Best GAT")
for seed in SEEDS:
    append_seed_table("GCN versus best GAT", seed, best_gat, "Best GAT")
lines.extend([r"\end{landscape}", r"\end{document}", ""])

OUTPUT.write_text("\n".join(lines))
print(f"Wrote {OUTPUT} from {len(expected)} matched runs per method")
