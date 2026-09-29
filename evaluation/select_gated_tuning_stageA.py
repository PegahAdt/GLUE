#!/usr/bin/env python3
"""Pareto-screen Stage A and emit at most three seed-robustness finalists."""
import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIGH = ["mean_average_precision", "normalized_mutual_info", "avg_silhouette_width",
        "avg_silhouette_width_batch", "graph_connectivity", "neighbor_conservation",
        "seurat_alignment_score"]
LOW = ["foscttm", "time"]
METRICS = HIGH + LOW

with (HERE / "gated_tuning_stageA_metrics.csv").open() as f:
    rows = list(csv.DictReader(f))
if len(rows) != 15:
    raise RuntimeError(f"Expected 15 Stage A rows, found {len(rows)}")
for row in rows:
    for key in METRICS:
        row[key] = float(row[key])
    for key in ("initial_gate_mean", "final_gate_min", "final_gate_mean", "final_gate_max",
                "maximum_absolute_gate_logit_change"):
        row[key] = float(row[key])
    row["pathology"] = []
    if row["maximum_absolute_gate_logit_change"] < 1e-3:
        row["pathology"].append("effectively frozen gates")
    if row["final_gate_mean"] < 0.25 or row["final_gate_mean"] < 0.5 * row["initial_gate_mean"]:
        row["pathology"].append("excessive mean gate collapse")
    if not 0 <= row["final_gate_min"] <= row["final_gate_mean"] <= row["final_gate_max"] <= 1:
        row["pathology"].append("invalid gate ordering/range")

valid = [r for r in rows if not r["pathology"]]
if not valid:
    raise RuntimeError("Every Stage A configuration has pathological gates")

def no_worse(a, b, metric):
    return a[metric] >= b[metric] if metric in HIGH else a[metric] <= b[metric]
def better(a, b, metric):
    return a[metric] > b[metric] if metric in HIGH else a[metric] < b[metric]
def dominates(a, b):
    return all(no_worse(a, b, m) for m in METRICS) and any(better(a, b, m) for m in METRICS)

front = [r for r in valid if not any(dominates(other, r) for other in valid if other is not r)]
baseline = next(r for r in rows if float(r["gate_init"]) == 0.95 and float(r["lam_keep"]) == 0)
for r in valid:
    r["baseline_wins"] = sum(better(r, baseline, m) for m in METRICS)
    ranks = []
    for m in HIGH:
        ordered = sorted(valid, key=lambda x: x[m], reverse=True)
        ranks.append(1 + ordered.index(r))
    r["quality_mean_rank"] = sum(ranks) / len(ranks)
front.sort(key=lambda r: (-r["baseline_wins"], r["quality_mean_rank"], r["time"], int(r["task_id"])))
finalists = front[:3]

md = ["# Stage A selection", "",
      "Feature consistency was deferred because a configuration-matched full-data reference is required.",
      "No weighted composite score was used. Configurations with non-finite metrics, effectively frozen gates,",
      "or excessive gate collapse were excluded. Pareto efficiency used all available metrics with their stated",
      "directions. If more than three configurations were non-dominated, the deterministic screen used number",
      "of wins over matched GATED, mean rank across higher-is-better quality metrics, runtime, then task ID.", "",
      f"Valid configurations: {len(valid)}; Pareto-optimal: {len(front)}.", "",
      "|task|gate_init|lam_keep|baseline wins|quality mean rank|runtime s|final gate mean|max logit change|selected|",
      "|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"]
for r in sorted(valid, key=lambda x: int(x["task_id"])):
    md.append(f"|{r['task_id']}|{r['gate_init']}|{r['lam_keep']}|{r['baseline_wins']}|"
              f"{r['quality_mean_rank']:.3f}|{r['time']:.3f}|{r['final_gate_mean']:.6f}|"
              f"{r['maximum_absolute_gate_logit_change']:.6f}|{'yes' if r in finalists else ''}|")
pathological = [r for r in rows if r["pathology"]]
if pathological:
    md += ["", "## Excluded gate pathologies", ""] + [
        f"- Task {r['task_id']}: {', '.join(r['pathology'])}" for r in pathological]
(HERE / "gated_tuning_stageA_selection.md").write_text("\n".join(md) + "\n")

with (HERE / "gated_tuning_stageB_configs.tsv").open("w", newline="") as f:
    fields = ["task_id", "gate_init", "lam_keep", "lam_graph", "subsample_size", "subsample_seed", "model_seed", "reuse_stageA"]
    w = csv.DictWriter(f, fieldnames=fields, delimiter="\t"); w.writeheader()
    tid = 0
    for finalist in finalists:
        for seed in (0, 1, 2):
            w.writerow({"task_id": tid, "gate_init": finalist["gate_init"], "lam_keep": finalist["lam_keep"],
                        "lam_graph": "0.02", "subsample_size": 2000, "subsample_seed": seed,
                        "model_seed": 0, "reuse_stageA": "yes" if seed == 0 else "no"})
            tid += 1
print("Finalists:", [(r["gate_init"], r["lam_keep"]) for r in finalists])
