#!/usr/bin/env python
"""Build strict nine-run GCN/GAT/GATED long and paired metric tables."""

from pathlib import Path
import pandas as pd
import yaml


OLD = Path("/project/6001426/paa40/GlUE_Exp/GLUE/evaluation")
OUT = Path("results_gated/comparison_10x_gcn_vs_gat_vs_gated")
PRIOR = "gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0"
HP = "dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10"
METRICS = [
    "mean_average_precision", "normalized_mutual_info", "avg_silhouette_width",
    "avg_silhouette_width_batch", "graph_connectivity", "foscttm",
    "neighbor_conservation", "feature_consistency", "seurat_alignment_score", "time",
]
ROOTS = {
    "gcn": OLD / "results_gcn_h100/raw",
    "gat": OLD / "results_gat/raw",
    "gated": Path("results_gated/raw"),
}

OUT.mkdir(parents=True, exist_ok=True)
rows, missing = [], []
for architecture, root in ROOTS.items():
    for size in (250, 2000, 8000):
        for seed in (0, 1, 2):
            path = root / "10x-Multiome-Pbmc10k" / f"subsample_size:{size}-subsample_seed:{seed}" / PRIOR / "GLUE" / HP / "seed:0/metrics.yaml"
            if not path.is_file() or not path.stat().st_size:
                missing.append(f"MISSING\t{architecture}\t{size}\t{seed}\t{path}")
                continue
            values = yaml.safe_load(path.read_text())
            for metric in METRICS:
                value = values.get(metric)
                if value is None:
                    missing.append(f"MISSING_METRIC\t{architecture}\t{size}\t{seed}\t{metric}\t{path}")
                else:
                    rows.append({"architecture": architecture, "size": size, "seed": seed, "metric": metric, "value": value})

(OUT / "missing_pairings.txt").write_text("\n".join(missing) + ("\n" if missing else ""))
long = pd.DataFrame(rows).sort_values(["size", "seed", "metric", "architecture"])
long.to_csv(OUT / "metrics_long.csv", index=False)
wide = long.pivot(index=["size", "seed", "metric"], columns="architecture", values="value").reset_index()
wide.columns.name = None
wide = wide[["size", "seed", "metric", "gcn", "gat", "gated"]]
wide.to_csv(OUT / "metrics_paired_wide.csv", index=False)

expected_long = 3 * 3 * len(METRICS) * 3
expected_wide = 3 * 3 * len(METRICS)
if missing or len(long) != expected_long or len(wide) != expected_wide or wide.isna().any().any():
    raise RuntimeError(f"Incomplete comparison: missing={len(missing)} long={len(long)}/{expected_long} wide={len(wide)}/{expected_wide}")
print(f"Validated {len(long)} long rows and {len(wide)} paired rows in {OUT}")
