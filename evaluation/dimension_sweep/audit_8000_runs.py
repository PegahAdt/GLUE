#!/usr/bin/env python3
"""Validate completed seed-0 8,000-cell dimension-sweep outputs."""
from pathlib import Path
import csv
import re
import yaml

ROOT = Path("/project/6001426/paa40/GlUE_Exp")
REPO = ROOT / "GLUE_GATED"
HERE = REPO / "evaluation/dimension_sweep"
SWEEP = REPO / "evaluation/results_dimension_sweep"
DIMS = (16, 32, 50, 64, 100)
ARCHES = ("gcn", "gat", "gated")
PRIOR = "gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0"
HP50 = "dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10"
BASE = {
    "gcn": ROOT / "GLUE/evaluation/results_gcn_h100/raw/10x-Multiome-Pbmc10k",
    "gat": ROOT / "GLUE/evaluation/results_gat/raw/10x-Multiome-Pbmc10k",
    "gated": REPO / "evaluation/results_gated/raw/10x-Multiome-Pbmc10k",
}

manifest = list(csv.DictReader((HERE / "job_manifest.csv").open()))


def path_for(arch, dim):
    if dim == 50:
        return BASE[arch] / "subsample_size:8000-subsample_seed:0" / PRIOR / "GLUE" / HP50 / "seed:0"
    return SWEEP / f"architecture:{arch}" / f"dim:{dim}" / "subsample_size:8000-subsample_seed:0/model_seed:0"


def csv_shape(path):
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        first = next(reader)
        rows = 1 + sum(1 for _ in reader)
    return rows, len(first) - 1  # headerless file; first column is the index


records = []
seen = set()
for arch in ARCHES:
    for dim in DIMS:
        directory = path_for(arch, dim).resolve()
        key = (arch, dim, 8000, 0, 0)
        assert key not in seen
        seen.add(key)
        required = ["rna_latent.csv", "atac_latent.csv", "feature_latent.csv", "run_info.yaml", "final.dill"]
        missing = [name for name in required if not (directory / name).is_file() or (directory / name).stat().st_size == 0]
        assert not missing, f"{key}: missing/nonempty check failed: {missing}"
        shapes = {name: csv_shape(directory / name) for name in ("rna_latent.csv", "atac_latent.csv", "feature_latent.csv")}
        assert shapes["rna_latent.csv"] == (8000, dim), (key, shapes)
        assert shapes["atac_latent.csv"] == (8000, dim), (key, shapes)
        assert shapes["feature_latent.csv"][1] == dim and shapes["feature_latent.csv"][0] > 0, (key, shapes)
        info = yaml.unsafe_load((directory / "run_info.yaml").read_text())
        args = info["args"]
        expected = {
            "graph_encoder": arch, "dim": dim, "alt_dim": 100, "hidden_depth": 2,
            "hidden_dim": 256, "dropout": 0.2, "lam_graph": 0.02, "lam_align": 0.05,
            "lr": 0.002, "neg_samples": 10, "data_batch_size": 128, "random_seed": 0,
        }
        if arch == "gat": expected["gat_negative_slope"] = 0.2
        if arch == "gated": expected.update(gate_init=0.95, lam_keep=0.0)
        bad = {k: (args.get(k), v) for k, v in expected.items() if args.get(k) != v}
        assert not bad, f"{key}: metadata mismatch {bad}"
        assert "subsample_size:8000-subsample_seed:0" in str(args["input_rna"])
        assert info.get("n_cells") == 16000 and float(info.get("time", 0)) > 0
        if dim == 50:
            job_id, state = "", "REUSED_VALIDATED"
            assert (directory / "metrics.yaml").stat().st_size > 0
        else:
            matches = [r for r in manifest if r["stage"] == "VALIDATION" and r["architecture"] == arch and int(r["dim"]) == dim and int(r["size"]) == 8000 and int(r["subsample_seed"]) == 0 and int(r["model_seed"]) == 0]
            assert len(matches) == 1, (key, matches)
            match = matches[0]
            assert match["job_id"] == "54328002" and match["exit_code"] == "0:0" and match["state"].startswith("COMPLETED")
            job_id, state = match["job_id"], "COMPLETED"
        records.append({
            "architecture": arch, "dim": dim, "size": 8000, "subsample_seed": 0,
            "model_seed": 0, "result_path": str(directory), "job_id": job_id,
            "state": state, "valid_for_metrics": "true",
        })

assert len(records) == 15 and len({r["result_path"] for r in records}) == 15
with (HERE / "available_8000_runs.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
print("Validated 15 unique seed-0 8,000-cell runs; all latent dimensions and metadata match.")
