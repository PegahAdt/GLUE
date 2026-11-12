#!/usr/bin/env python3
"""Collect accepted 8,000-cell metrics and combine with authoritative 2,000-cell data."""
from pathlib import Path
import csv
import yaml

HERE = Path(__file__).resolve().parent
RUNS = list(csv.DictReader((HERE / "available_8000_runs.csv").open()))
METRICS = (
    "mean_average_precision", "normalized_mutual_info", "avg_silhouette_width",
    "avg_silhouette_width_batch", "graph_connectivity", "foscttm",
    "neighbor_conservation", "feature_consistency", "seurat_alignment_score",
)

wide = []
long = []
for run in RUNS:
    arch, dim = run["architecture"], int(run["dim"])
    result = Path(run["result_path"])
    metric_file = result / "metrics.yaml" if dim == 50 else HERE / "metrics_8000_runs" / arch / f"dim_{dim}" / "seed_0/metrics.yaml"
    assert metric_file.is_file() and metric_file.stat().st_size > 0, metric_file
    data = yaml.unsafe_load(metric_file.read_text())
    record = {
        "architecture": arch, "dim": dim, "size": 8000, "subsample_seed": 0,
        "model_seed": 0, "MAP": data["mean_average_precision"],
        "NMI": data["normalized_mutual_info"], "ASW": data["avg_silhouette_width"],
        "Batch ASW": data["avg_silhouette_width_batch"],
        "Graph connectivity": data["graph_connectivity"], "FOSCTTM": data["foscttm"],
        "Neighbor consistency": data["neighbor_conservation"],
        "Feature consistency": data.get("feature_consistency") if dim == 50 else "NA",
        "Seurat alignment": data["seurat_alignment_score"], "Runtime": data["time"],
        "result_path": str(result),
    }
    wide.append(record)
    for metric in METRICS:
        value = data.get(metric) if metric != "feature_consistency" or dim == 50 else None
        long.append({
            "architecture": arch, "dim": dim, "size": 8000, "subsample_seed": 0,
            "model_seed": 0, "metric": metric, "value": "NA" if value is None else value,
            "runtime": data["time"], "result_path": str(result),
        })

assert len(wide) == 15 and len(long) == 135
assert len({(r["architecture"], r["dim"], r["size"], r["subsample_seed"], r["model_seed"]) for r in wide}) == 15
with (HERE / "metrics_8000_wide.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(wide[0]))
    writer.writeheader(); writer.writerows(wide)
with (HERE / "metrics_8000_long.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(long[0]))
    writer.writeheader(); writer.writerows(long)

# Normalize the 2,000-cell authoritative long source and append the 8,000-cell records.
combined = []
for row in csv.DictReader((HERE / "stageA_metrics_long.csv").open()):
    combined.append({
        "architecture": row["architecture"], "dim": row["dimension"], "size": row["size"],
        "subsample_seed": row["subsample_seed"], "model_seed": row["model_seed"],
        "metric": row["metric"], "value": row["value"], "runtime": row["runtime"],
        "result_path": row["result_path"],
    })
combined.extend(long)
assert len(combined) == 270
with (HERE / "metrics_2000_8000_combined.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(combined[0]))
    writer.writeheader(); writer.writerows(combined)
print("Collected 15 8,000-cell configurations and 270 combined long records.")
