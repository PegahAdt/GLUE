#!/usr/bin/env python
"""Prove that the nine prepared GCN/GAT subsamples have identical cell IDs."""

import argparse
import hashlib
from pathlib import Path

import anndata


OLD = Path("/project/6001426/paa40/GlUE_Exp/GLUE/evaluation")
ROOTS = {"gcn": OLD / "results_gcn_h100/raw", "gat": OLD / "results_gat/raw"}
DATASET = "10x-Multiome-Pbmc10k"


def names(path: Path):
    adata = anndata.read_h5ad(path, backed="r")
    try:
        return tuple(map(str, adata.obs_names))
    finally:
        adata.file.close()


def digest(values):
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--size", type=int, choices=(250, 2000, 8000))
parser.add_argument("--seed", type=int, choices=(0, 1, 2))
args = parser.parse_args()
sizes = (args.size,) if args.size is not None else (250, 2000, 8000)
seeds = (args.seed,) if args.seed is not None else (0, 1, 2)

for size in sizes:
    for seed in seeds:
        conf = f"subsample_size:{size}-subsample_seed:{seed}"
        hashes = {}
        for architecture, root in ROOTS.items():
            data = root / DATASET / conf
            rna = names(data / "rna.h5ad")
            atac = names(data / "atac.h5ad")
            if rna != atac:
                raise RuntimeError(f"RNA/ATAC cell order differs: {architecture} {conf}")
            hashes[architecture] = digest(rna)
        if hashes["gcn"] != hashes["gat"]:
            raise RuntimeError(f"GCN/GAT cell IDs differ: {conf}")
        print(f"MATCH size={size} seed={seed} cells={size} sha256={hashes['gcn']}")
