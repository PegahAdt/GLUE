#!/bin/bash
#SBATCH --job-name=smoke_10x_glue
#SBATCH --time=4:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=smoke_10x_glue_%j.out
#SBATCH --error=smoke_10x_glue_%j.err

set -eo pipefail

cd /project/6001426/paa40/GLUE/GLUE

source activate_glue.sh

python - <<'PY'
from itertools import chain
from pathlib import Path

import anndata as ad
import networkx as nx
import numpy as np
import scglue

outdir = Path("results/10x_smoke")
outdir.mkdir(parents=True, exist_ok=True)

print("scglue:", scglue.__version__)

rna = ad.read_h5ad("data/dataset/10x-Multiome-Pbmc10k-RNA-glue-ready.h5ad")
atac = ad.read_h5ad("data/dataset/10x-Multiome-Pbmc10k-ATAC-glue-ready.h5ad")
guidance = nx.read_graphml("data/dataset/10x-Multiome-Pbmc10k-guidance.graphml.gz")

print("Original RNA:", rna.shape)
print("Original ATAC:", atac.shape)
print("Original graph:", guidance.number_of_nodes(), "nodes,", guidance.number_of_edges(), "edges")

# Small paired-cell smoke test
n_cells = min(1000, rna.n_obs, atac.n_obs)
common = rna.obs_names.intersection(atac.obs_names)
if len(common) >= n_cells:
    keep_cells = common[:n_cells]
    rna = rna[keep_cells].copy()
    atac = atac[keep_cells].copy()
else:
    rna = rna[:n_cells].copy()
    atac = atac[:n_cells].copy()

# Keep RNA HV genes
rna = rna[:, rna.var["highly_variable"].to_numpy()].copy()

# Keep a manageable number of ATAC peaks connected to RNA HV genes
gene_nodes = set(rna.var_names).intersection(guidance.nodes)
peak_nodes = set(atac.var_names).intersection(guidance.nodes)

connected_peaks = []
for u, v in guidance.edges():
    if u in gene_nodes and v in peak_nodes:
        connected_peaks.append(v)
    elif v in gene_nodes and u in peak_nodes:
        connected_peaks.append(u)

connected_peaks = list(dict.fromkeys(connected_peaks))
if len(connected_peaks) == 0:
    raise RuntimeError("No connected ATAC peaks found between RNA HV genes and ATAC peaks.")

keep_peaks = connected_peaks[:5000]
atac = atac[:, keep_peaks].copy()
atac.var["highly_variable"] = True

# Subset graph to selected features
feature_names = list(chain(rna.var_names, atac.var_names))
guidance = guidance.subgraph(feature_names).copy()

print("Smoke RNA:", rna.shape)
print("Smoke ATAC:", atac.shape)
print("Smoke graph:", guidance.number_of_nodes(), "nodes,", guidance.number_of_edges(), "edges")

print("Configuring datasets...")
scglue.models.configure_dataset(
    rna, "NB",
    use_highly_variable=True,
    use_layer="counts",
    use_rep="X_pca"
)

scglue.models.configure_dataset(
    atac, "NB",
    use_highly_variable=True,
    use_layer="counts",
    use_rep="X_lsi"
)

print("Training small SCGLUE smoke model...")
glue = scglue.models.fit_SCGLUE(
    {"rna": rna, "atac": atac},
    guidance,
    fit_kws={
        "directory": str(outdir / "fit"),
        "max_epochs": 2
    }
)

print("Encoding cells...")
rna.obsm["X_glue"] = glue.encode_data("rna", rna)
atac.obsm["X_glue"] = glue.encode_data("atac", atac)

print("RNA X_glue:", rna.obsm["X_glue"].shape)
print("ATAC X_glue:", atac.obsm["X_glue"].shape)

rna.write(outdir / "rna_smoke_glue.h5ad", compression="gzip")
atac.write(outdir / "atac_smoke_glue.h5ad", compression="gzip")

if hasattr(glue, "save"):
    glue.save(outdir / "glue_smoke.dill")

print("Wrote smoke-test outputs to:", outdir)
PY
