#!/usr/bin/env python3
"""Compute missing gate-init metrics from saved embeddings only (no training)."""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path("/project/6001426/paa40/GlUE_Exp/GLUE")
GATED_ROOT = Path("/project/6001426/paa40/GlUE_Exp/GLUE_GATED")
OUT = ROOT / "evaluation/gate_init_sensitivity_metrics"
INVENTORY = ROOT / "evaluation/gate_init_sensitivity_report/run_inventory.csv"
CELL_SCRIPT = ROOT / "evaluation/workflow/scripts/cell_integration.py"
FEATURE_SCRIPT = ROOT / "evaluation/workflow/scripts/feature_consistency.py"
REFERENCE_FEATURE = (
    GATED_ROOT / "evaluation/results_gated/raw/10x-Multiome-Pbmc10k/original/"
    "gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/GLUE/"
    "dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-"
    "lam_graph:0.02-lam_align:0.05-neg_samples:10/seed:0/feature_latent.csv"
)
EXPECTED_METRICS = {
    "mean_average_precision", "normalized_mutual_info", "avg_silhouette_width",
    "avg_silhouette_width_batch", "graph_connectivity", "foscttm",
    "neighbor_conservation", "feature_consistency", "seurat_alignment_score",
    "time",
}


def resolve_path(configured: str) -> Path:
    clean = Path(configured)
    found = [p for p in (clean, Path(configured + "\r")) if p.exists()]
    if len(found) != 1:
        raise RuntimeError(f"Expected one result path for {configured!r}, found {found}")
    return found[0]


def load_tasks() -> list[dict]:
    rows = list(csv.DictReader(INVENTORY.open(newline="")))
    if len(rows) != 45 or any(row["status"] != "complete" for row in rows):
        raise RuntimeError("Validated inventory must contain exactly 45 complete runs")
    tasks = []
    for row in rows:
        path = resolve_path(row["configured_path"])
        info = yaml.unsafe_load((path / "run_info.yaml").read_text())
        args = info["args"]
        expected = (float(row["gate_init"]), int(row["subset_size"]), int(row["seed"]))
        checks = {
            "gate_init": math.isclose(float(args["gate_init"]), expected[0], abs_tol=1e-12),
            "graph_encoder": args.get("graph_encoder") == "gated",
            "lam_keep": math.isclose(float(args.get("lam_keep", math.nan)), 0.0, abs_tol=1e-15),
            "model_seed": int(args.get("random_seed", -1)) == int(row["model_seed"]),
            "subset": f"subsample_size:{expected[1]}-subsample_seed:{expected[2]}" in str(args["input_rna"]),
        }
        failed = [name for name, valid in checks.items() if not valid]
        if failed:
            raise RuntimeError(f"Metadata mismatch at {path}: {failed}")
        required = [path / name for name in ("rna_latent.csv", "atac_latent.csv", "feature_latent.csv")]
        input_rna, input_atac = Path(args["input_rna"]), Path(args["input_atac"])
        required += [input_rna.with_name("rna_unirep.h5ad"), input_atac.with_name("atac_unirep.h5ad")]
        missing = [str(p) for p in required if not p.is_file() or p.stat().st_size == 0]
        if missing:
            raise RuntimeError(f"Missing evaluation inputs for {expected}: {missing}")
        existing = path / "metrics.yaml"
        if existing.is_file() and existing.stat().st_size:
            metrics = yaml.safe_load(existing.read_text())
            if not EXPECTED_METRICS.issubset(metrics):
                raise RuntimeError(f"Existing metrics incomplete at {existing}")
            continue
        tasks.append({"row": row, "path": path, "info": info, "input_rna": input_rna, "input_atac": input_atac})
    return sorted(tasks, key=lambda x: (float(x["row"]["gate_init"]), int(x["row"]["subset_size"]), int(x["row"]["seed"])))


def task_dir(task: dict) -> Path:
    row = task["row"]
    return OUT / "per_run" / f"gate_init_{float(row['gate_init']):.2f}" / f"subset_{int(row['subset_size'])}" / f"seed_{int(row['seed'])}"


def run_task(task: dict) -> None:
    dest = task_dir(task)
    dest.mkdir(parents=True, exist_ok=True)
    path, info = task["path"], task["info"]
    cell_yaml, feature_yaml = dest / "cell_integration.yaml", dest / "feature_consistency.yaml"
    log_cell, log_feature = dest / "cell_integration.log", dest / "feature_consistency.log"
    cell_cmd = [
        sys.executable, str(CELL_SCRIPT), "-d", str(task["input_rna"].with_name("rna_unirep.h5ad")),
        str(task["input_atac"].with_name("atac_unirep.h5ad")), "-l",
        str(path / "rna_latent.csv"), str(path / "atac_latent.csv"),
        "--cell-type", "cell_type", "--domain", "domain", "-p", "-o", str(cell_yaml),
    ]
    feature_cmd = [
        sys.executable, str(FEATURE_SCRIPT), "-q", str(path / "feature_latent.csv"),
        "-r", str(REFERENCE_FEATURE), "-f", "2000", "-p", "4", "-s", "0", "-o", str(feature_yaml),
    ]
    with log_cell.open("w") as log:
        subprocess.run(cell_cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    with log_feature.open("w") as log:
        subprocess.run(feature_cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    metrics = {}
    metrics.update({k: v for k, v in info.items() if k not in {"args"}})
    metrics.update(yaml.safe_load(cell_yaml.read_text()))
    metrics.update(yaml.safe_load(feature_yaml.read_text()))
    missing = EXPECTED_METRICS - set(metrics)
    if missing:
        raise RuntimeError(f"Computed metrics missing {sorted(missing)} at {dest}")
    (dest / "metrics.yaml").write_text(yaml.safe_dump(metrics, sort_keys=True))
    print(f"WROTE {dest / 'metrics.yaml'}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--task-index", type=int)
    args = parser.parse_args()
    tasks = load_tasks()
    if len(tasks) != 36:
        raise RuntimeError(f"Expected 36 missing metric tasks, found {len(tasks)}")
    if args.list:
        for i, task in enumerate(tasks):
            row = task["row"]
            print(i, row["gate_init"], row["subset_size"], row["seed"], task["path"], sep="\t")
        return
    if args.task_index is None or not 0 <= args.task_index < len(tasks):
        parser.error(f"--task-index must be in [0, {len(tasks) - 1}]")
    run_task(tasks[args.task_index])


if __name__ == "__main__":
    main()
