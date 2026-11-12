#!/usr/bin/env python3
"""Collect only small YAML outputs from the bounded Stage A search."""
import csv
import math
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
rows = []
with (HERE / "gated_tuning_stageA_configs.tsv").open() as f:
    for cfg in csv.DictReader(f, delimiter="\t"):
        tag = (f"gate_init:{cfg['gate_init']}-lam_keep:{cfg['lam_keep']}-lam_graph:0.02-"
               f"size:{cfg['subsample_size']}-subsample_seed:{cfg['subsample_seed']}-"
               f"model_seed:{cfg['model_seed']}")
        dest = HERE / "results_gated_tuning/stageA" / tag
        source = Path((dest / "REUSED_FROM").read_text().strip()) if (dest / "REUSED_FROM").is_file() else dest
        with (dest / "metrics.yaml").open() as fmet, (source / "gate_diagnostics.yaml").open() as fgate:
            values = {**yaml.safe_load(fmet), **yaml.safe_load(fgate)}
        wanted = ["mean_average_precision", "normalized_mutual_info", "avg_silhouette_width",
                  "avg_silhouette_width_batch", "graph_connectivity", "foscttm",
                  "neighbor_conservation", "seurat_alignment_score", "time",
                  "number_of_trainable_gates", "initial_gate_mean", "final_gate_min",
                  "final_gate_mean", "final_gate_max", "maximum_absolute_gate_logit_change"]
        for key in wanted:
            if key not in values or not math.isfinite(float(values[key])):
                raise RuntimeError(f"Missing/nonfinite {key}: {dest}")
        rows.append({**cfg, "lam_graph": "0.02", **{k: values[k] for k in wanted},
                     "feature_consistency": "DEFERRED_CONFIG_MATCHED_REFERENCE", "result_dir": str(dest)})
out = HERE / "gated_tuning_stageA_metrics.csv"
with out.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader(); writer.writerows(rows)
print(f"Wrote {len(rows)} finite configurations to {out}")
