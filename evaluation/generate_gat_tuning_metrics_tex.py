"""Generate a standalone LaTeX table for all completed GAT tuning runs."""

from pathlib import Path
import csv
import re

import yaml


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results_gat_tuning" / "screen_v2"
OUTPUT = ROOT / "gat_tuning_metrics_by_configuration.tex"
CONFIGS = ROOT / "gat_tuning_10x" / "screen_v1" / "configs.tsv"

FIXED_PARAMETERS = (
    ("dim", "50"),
    ("alt_dim", "100"),
    ("hidden_depth", "2"),
    ("hidden_dim", "256"),
    ("dropout", "0.2"),
    ("neg_samples", "10"),
)

METRICS = (
    ("mean_average_precision", "MAP"),
    ("normalized_mutual_info", "NMI"),
    ("avg_silhouette_width", "ASW"),
    ("avg_silhouette_width_batch", "Batch ASW"),
    ("graph_connectivity", "Graph conn."),
    ("foscttm", "FOSCTTM"),
    ("neighbor_conservation", "Neighbor cons."),
    ("feature_consistency", "Feature cons."),
    ("seurat_alignment_score", "Seurat align."),
    ("time", "Time (h)"),
)


def escape(text):
    return str(text).replace("_", r"\_")


def number(value, key):
    if value is None:
        return r"\textemdash"
    if key == "time":
        value = value / 3600
    return f"{float(value):.4f}"


rows = []
for path in RESULTS.glob("*/raw/**/metrics.yaml"):
    relative = path.relative_to(RESULTS)
    configuration = relative.parts[0]
    match = re.search(
        r"subsample_size:(\d+)-subsample_seed:(\d+)", path.as_posix()
    )
    if match is None:
        continue
    size, seed = map(int, match.groups())
    with path.open() as stream:
        values = yaml.safe_load(stream)
    rows.append((configuration, size, seed, values))

rows.sort(key=lambda row: (row[0], row[1], row[2]))

with CONFIGS.open(newline="") as stream:
    tested_parameters = {
        row["config_name"]: (
            ("lr", row["lr"]),
            ("lam_graph", row["lam_graph"]),
            ("lam_align", row["lam_align"]),
            ("gat_negative_slope", row["gat_negative_slope"]),
            *FIXED_PARAMETERS,
        )
        for row in csv.DictReader(stream, delimiter="\t")
    }

lines = [
    r"\documentclass[10pt]{article}",
    r"\usepackage[margin=0.45in]{geometry}",
    r"\usepackage{booktabs}",
    r"\usepackage{longtable}",
    r"\usepackage{pdflscape}",
    r"\usepackage{array}",
    r"\setlength{\tabcolsep}{3.2pt}",
    r"\renewcommand{\arraystretch}{1.08}",
    r"\begin{document}",
    r"\begin{landscape}",
    r"\section*{GAT tuning metrics by configuration}",
    (
        r"Each row is one completed configuration--subsample-size--seed run from "
        r"\texttt{results\_gat\_tuning/screen\_v2}. Higher is better except for "
        r"FOSCTTM and runtime."
    ),
    r"\footnotesize",
]

configurations = sorted({row[0] for row in rows})
for index, configuration in enumerate(configurations):
    config_rows = [row for row in rows if row[0] == configuration]
    label = re.sub(r"[^a-zA-Z0-9]+", "-", configuration).strip("-").lower()
    parameter_cells = [
        rf"\texttt{{{escape(key)}={escape(value)}}}"
        for key, value in tested_parameters[configuration]
    ]
    lines.extend(
        [
            rf"\subsection*{{Configuration: \texttt{{{escape(configuration)}}}}}",
            r"\noindent\textbf{Complete model configuration tested:}",
            r"\begin{center}",
            r"\begin{tabular}{@{}lllll@{}}",
            " & ".join(parameter_cells[:5]) + r" \\",
            " & ".join(parameter_cells[5:]) + r" \\",
            r"\end{tabular}",
            r"\end{center}",
            (
                r"\noindent\textbf{Evaluation setup:} "
                r"\texttt{gene\_region=combined}, "
                r"\texttt{extend\_range=0}, "
                r"\texttt{corrupt\_rate=0.0}, "
                r"\texttt{corrupt\_seed=0}, model seed 0; table rows vary "
                r"subsample size and subsample seed."
            ),
            r"\vspace{4pt}",
            r"\begin{longtable}{rr*{10}{r}}",
            (
                f"\\caption{{All available metrics for configuration "
                f"\\texttt{{{escape(configuration)}}}.}}"
                f"\\label{{tab:gat-tuning-{label}}}\\\\"
            ),
            r"\toprule",
            r"Size & Seed & MAP & NMI & ASW & Batch ASW & Graph conn. & "
            r"FOSCTTM & Neighbor cons. & Feature cons. & Seurat align. & Time (h) \\",
            r"\midrule",
            r"\endfirsthead",
            r"\toprule",
            r"Size & Seed & MAP & NMI & ASW & Batch ASW & Graph conn. & "
            r"FOSCTTM & Neighbor cons. & Feature cons. & Seurat align. & Time (h) \\",
            r"\midrule",
            r"\endhead",
            r"\midrule",
            r"\multicolumn{12}{r}{Continued on next page}\\",
            r"\endfoot",
            r"\bottomrule",
            r"\endlastfoot",
        ]
    )
    for _, size, seed, values in config_rows:
        cells = [str(size), str(seed)]
        cells.extend(number(values.get(key), key) for key, _ in METRICS)
        lines.append(" & ".join(cells) + r" \\")
    lines.append(r"\end{longtable}")
    if index != len(configurations) - 1:
        lines.append(r"\clearpage")

lines.extend(
    [
        f"\\noindent Completed runs included: {len(rows)}.",
        r"\end{landscape}",
        r"\end{document}",
        "",
    ]
)

OUTPUT.write_text("\n".join(lines))
print(f"Wrote {OUTPUT} with {len(rows)} rows")
