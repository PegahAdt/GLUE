from pathlib import Path
import sys
import yaml
import pandas as pd

if len(sys.argv) != 2:
    raise SystemExit("Usage: python collect_metrics_from_targets.py <target_file.txt>")

target_file = Path(sys.argv[1])

rows = []
missing = []

for line in target_file.read_text().splitlines():
    line = line.strip()
    if not line:
        continue

    p = Path(line)

    if not p.exists() or p.stat().st_size == 0:
        missing.append(str(p))
        continue

    with open(p) as f:
        m = yaml.safe_load(f)

    parts = p.parts
    dataset = parts[2]
    data_conf = parts[3]
    method = parts[5]
    hyperparam_conf = parts[6]
    method_seed = parts[7]

    subsample_size = int(data_conf.split("subsample_size:")[1].split("-")[0])
    subsample_seed = int(data_conf.split("subsample_seed:")[1])
    seed = int(method_seed.split("seed:")[1])

    rows.append({
        "dataset": dataset,
        "subsample_size": subsample_size,
        "subsample_seed": subsample_seed,
        "method_seed": seed,
        "method": method,
        "n_cells": m.get("n_cells"),
        "time_seconds": m.get("time"),
        "time_hours": None if m.get("time") is None else m.get("time") / 3600,
        "mean_average_precision": m.get("mean_average_precision"),
        "normalized_mutual_info": m.get("normalized_mutual_info"),
        "avg_silhouette_width": m.get("avg_silhouette_width"),
        "avg_silhouette_width_batch": m.get("avg_silhouette_width_batch"),
        "graph_connectivity": m.get("graph_connectivity"),
        "foscttm": m.get("foscttm"),
        "neighbor_conservation": m.get("neighbor_conservation"),
        "feature_consistency": m.get("feature_consistency"),
        "seurat_alignment_score": m.get("seurat_alignment_score"),
        "metrics_path": str(p),
    })

df = pd.DataFrame(rows)

if not df.empty:
    df = df.sort_values(["dataset", "subsample_size", "subsample_seed", "method_seed"])

out = Path("results") / f"{target_file.stem}_metrics.csv"
missing_out = Path("results") / f"{target_file.stem}_missing.txt"

out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
missing_out.write_text("\n".join(missing) + ("\n" if missing else ""))

print("Target file:", target_file)
print("Completed:", len(rows))
print("Missing:", len(missing))
print("Wrote metrics:", out)
print("Wrote missing list:", missing_out)

if not df.empty:
    print()
    cols = [
        "dataset",
        "subsample_size",
        "subsample_seed",
        "method_seed",
        "n_cells",
        "mean_average_precision",
        "normalized_mutual_info",
        "avg_silhouette_width",
        "foscttm",
        "feature_consistency",
        "time_hours",
    ]
    print(df[cols].to_string(index=False))
