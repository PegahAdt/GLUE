"""Run an adaptive, time-bounded GAT search inside one Slurm GPU allocation."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
WORKFLOW = ROOT / "workflow_gat_10x" / "scripts"
SOURCE = ROOT / "results_gat_tuning" / "screen_v2" / "graph_0p05" / "raw"
OUTPUT = ROOT / "results_gat_manual_search"

# The first screen combines the two strongest one-factor findings and explores
# a small neighborhood around the current best graph/alignment weights.
CANDIDATES = {
    "g040_a050_s010": dict(lr=0.002, lam_graph=0.04, lam_align=0.05, slope=0.10),
    "g050_a040_s010": dict(lr=0.002, lam_graph=0.05, lam_align=0.04, slope=0.10),
    "g050_a050_s010": dict(lr=0.002, lam_graph=0.05, lam_align=0.05, slope=0.10),
    "g050_a060_s010": dict(lr=0.002, lam_graph=0.05, lam_align=0.06, slope=0.10),
    "g060_a050_s010": dict(lr=0.002, lam_graph=0.06, lam_align=0.05, slope=0.10),
}

METRICS = (
    "mean_average_precision",
    "normalized_mutual_info",
    "avg_silhouette_width",
    "avg_silhouette_width_batch",
    "graph_connectivity",
    "foscttm",
    "neighbor_conservation",
    "feature_consistency",
    "seurat_alignment_score",
)


def unique(pattern: str) -> Path:
    matches = list(SOURCE.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one match for {pattern}, found {len(matches)}")
    return matches[0]


REFERENCE_FEATURE = unique(
    "10x-Multiome-Pbmc10k/original/**/"
    "dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-"
    "lam_graph:0.02-lam_align:0.05-neg_samples:10/seed:0/feature_latent.csv"
)


def source_data(size: int, seed: int) -> Path:
    return unique(
        f"10x-Multiome-Pbmc10k/subsample_size:{size}-subsample_seed:{seed}"
    )


def run_logged(command: list[str], log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as stream:
        subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)


def run_candidate(name: str, params: dict[str, float], size: int, seed: int) -> Path:
    data = source_data(size, seed)
    prior = next(data.glob("gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/sub.graphml.gz"))
    out = OUTPUT / name / f"size_{size}_seed_{seed}"
    out.mkdir(parents=True, exist_ok=True)
    metrics = out / "metrics.yaml"
    if metrics.is_file() and metrics.stat().st_size:
        return metrics

    parameters = {
        **params,
        "dim": 50,
        "alt_dim": 100,
        "hidden_depth": 2,
        "hidden_dim": 256,
        "dropout": 0.2,
        "neg_samples": 10,
        "subsample_size": size,
        "subsample_seed": seed,
        "model_seed": 0,
    }
    (out / "parameters.yaml").write_text(yaml.safe_dump(parameters, sort_keys=False))

    run_logged(
        [
            sys.executable, "workflow_gat_10x/scripts/run_GLUE.py",
            "--input-rna", str(data / "rna.h5ad"),
            "--input-atac", str(data / "atac.h5ad"),
            "-p", str(prior), "-d", "50", "--alt-dim", "100",
            "--hidden-depth", "2", "--hidden-dim", "256", "--dropout", "0.2",
            "--lr", str(params["lr"]), "--lam-graph", str(params["lam_graph"]),
            "--lam-align", str(params["lam_align"]), "--neg-samples", "10",
            "--graph-encoder", "gat", "--gat-negative-slope", str(params["slope"]),
            "-s", "0", "--train-dir", str(out), "--require-converge",
            "--output-rna", str(out / "rna_latent.csv"),
            "--output-atac", str(out / "atac_latent.csv"),
            "--output-feature", str(out / "feature_latent.csv"),
            "--run-info", str(out / "run_info.yaml"),
        ],
        out / "run_GLUE.log",
    )
    run_logged(
        [sys.executable, "workflow_gat_10x/scripts/feature_consistency.py",
         "-q", str(out / "feature_latent.csv"), "-r", str(REFERENCE_FEATURE),
         "-o", str(out / "feature_consistency.yaml")],
        out / "feature_consistency.log",
    )
    run_logged(
        [sys.executable, "workflow_gat_10x/scripts/cell_integration.py",
         "-d", str(data / "rna_unirep.h5ad"), str(data / "atac_unirep.h5ad"),
         "-l", str(out / "rna_latent.csv"), str(out / "atac_latent.csv"),
         "--cell-type", "cell_type", "--domain", "domain", "-p",
         "-o", str(out / "cell_integration.yaml")],
        out / "cell_integration.log",
    )
    run_logged(
        [sys.executable, "workflow_gat_10x/scripts/combine_metrics.py", "-i",
         str(out / "run_info.yaml"), str(out / "cell_integration.yaml"),
         str(out / "feature_consistency.yaml"), "-o", str(metrics)],
        out / "combine_metrics.log",
    )
    return metrics


def rank_screen(paths: dict[str, Path]) -> tuple[str, dict[str, float]]:
    values = {name: yaml.safe_load(path.read_text()) for name, path in paths.items()}
    scores = {name: 0.0 for name in paths}
    for metric in METRICS:
        ordered = sorted(
            paths,
            key=lambda name: values[name][metric],
            reverse=(metric != "foscttm"),
        )
        denominator = max(len(ordered) - 1, 1)
        for rank, name in enumerate(ordered):
            scores[name] += 1.0 - rank / denominator
    scores = {name: score / len(METRICS) for name, score in scores.items()}
    return max(scores, key=scores.get), scores


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    screen = {}
    for name, params in CANDIDATES.items():
        print(f"SCREEN {name}: size=2000 seed=0", flush=True)
        screen[name] = run_candidate(name, params, 2000, 0)
    winner, scores = rank_screen(screen)
    print(f"SCREEN WINNER: {winner} ({scores[winner]:.4f})", flush=True)
    validation = [(2000, 1), (2000, 2), (250, 0), (8000, 0)]
    for size, seed in validation:
        print(f"VALIDATE {winner}: size={size} seed={seed}", flush=True)
        run_candidate(winner, CANDIDATES[winner], size, seed)
    summary = {
        "winner": winner,
        "winner_parameters": CANDIDATES[winner],
        "screen_scores": scores,
        "screen_condition": {"size": 2000, "seed": 0},
        "validation_conditions": [dict(size=size, seed=seed) for size, seed in validation],
    }
    (OUTPUT / "search_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
