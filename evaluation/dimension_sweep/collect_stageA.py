#!/usr/bin/env python3
"""Collect validated Stage-A dimension metrics without recomputing them."""
from pathlib import Path
import csv
import yaml

ROOT = Path("/project/6001426/paa40/GlUE_Exp")
HERE = ROOT / "GLUE_GATED/evaluation/dimension_sweep"
PRIOR = "gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0"
HP50 = "dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10"
BASE = {
    "gcn": ROOT / "GLUE/evaluation/results_gcn_h100/raw/10x-Multiome-Pbmc10k",
    "gat": ROOT / "GLUE/evaluation/results_gat/raw/10x-Multiome-Pbmc10k",
    "gated": ROOT / "GLUE_GATED/evaluation/results_gated/raw/10x-Multiome-Pbmc10k",
}
METRICS = (
    "mean_average_precision", "normalized_mutual_info", "avg_silhouette_width",
    "avg_silhouette_width_batch", "graph_connectivity", "foscttm",
    "neighbor_conservation", "seurat_alignment_score", "feature_consistency",
)


def result_dir(arch, dim):
    if dim == 50:
        return BASE[arch] / "subsample_size:2000-subsample_seed:0" / PRIOR / "GLUE" / HP50 / "seed:0"
    return (ROOT / "GLUE_GATED/evaluation/results_dimension_sweep" /
            f"architecture:{arch}" / f"dim:{dim}" /
            "subsample_size:2000-subsample_seed:0/model_seed:0")


rows = []
wide = []
for arch in ("gcn", "gat", "gated"):
    for dim in (16, 32, 50, 64, 100):
        directory = result_dir(arch, dim)
        data = yaml.safe_load((directory / "metrics.yaml").read_text())
        base_record = {
            "architecture": arch, "dimension": dim, "size": 2000,
            "subsample_seed": 0, "model_seed": 0,
            "runtime": data["time"], "result_path": str(directory),
        }
        record = dict(base_record)
        for metric in METRICS:
            value = data.get(metric) if metric != "feature_consistency" or dim == 50 else None
            rows.append({**base_record, "metric": metric, "value": "NA" if value is None else value})
            record[metric] = "NA" if value is None else value
        wide.append(record)

fields = ["architecture", "dimension", "size", "subsample_seed", "model_seed",
          "metric", "value", "runtime", "result_path"]
with (HERE / "stageA_metrics_long.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
with (HERE / "stageA_metrics.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(wide[0]))
    writer.writeheader()
    writer.writerows(wide)
print(f"Collected {len(wide)} valid configurations and {len(rows)} metric records")
