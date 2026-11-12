#!/bin/bash
#SBATCH --job-name=glue_10x_full
#SBATCH --time=24:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
#SBATCH --output=logs/glue_10x_full_%j.out
#SBATCH --error=logs/glue_10x_full_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
mkdir -p logs results/10x_full

source /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/activate_glue.sh

python - <<'PY'
from pathlib import Path
import anndata as ad
import scanpy as sc
import scglue
import networkx as nx
import numpy as np

outdir = Path("results/10x_full")
outdir.mkdir(parents=True, exist_ok=True)

print("Reading full 10x Multiome data...")
rna = ad.read_h5ad("data/dataset/10x-Multiome-Pbmc10k-RNA.h5ad")
atac = ad.read_h5ad("data/dataset/10x-Multiome-Pbmc10k-ATAC.h5ad")

print("RNA:", rna.shape)
print("ATAC:", atac.shape)

print("Saving raw count layers...")
rna.layers["counts"] = rna.X.copy()
atac.layers["counts"] = atac.X.copy()

print("Preprocessing RNA...")
sc.pp.normalize_total(rna)
sc.pp.log1p(rna)

if "highly_variable" not in rna.var:
    print("RNA missing highly_variable column; computing HVGs...")
    sc.pp.highly_variable_genes(rna, n_top_genes=2000, flavor="seurat")

sc.pp.scale(rna, max_value=10)
sc.tl.pca(
    rna,
    n_comps=100,
    use_highly_variable=True,
    svd_solver="auto"
)

print("Preprocessing ATAC...")
atac.var["highly_variable"] = True
scglue.data.lsi(atac, n_components=100, n_iter=15)

print("Building guidance graph...")
guidance = scglue.genomics.rna_anchored_prior_graph(rna, atac)

print("Guidance graph:")
print("  nodes:", guidance.number_of_nodes())
print("  edges:", guidance.number_of_edges())

print("Configuring datasets...")
scglue.models.configure_dataset(
    rna,
    "NB",
    use_highly_variable=True,
    use_layer="counts",
    use_rep="X_pca"
)

scglue.models.configure_dataset(
    atac,
    "NB",
    use_highly_variable=True,
    use_layer="counts",
    use_rep="X_lsi"
)

print("Training full GLUE model...")
glue = scglue.models.fit_SCGLUE(
    {"rna": rna, "atac": atac},
    guidance,
    fit_kws={
        "directory": str(outdir / "fit")
    }
)

print("Encoding cells...")
rna.obsm["X_glue"] = glue.encode_data("rna", rna)
atac.obsm["X_glue"] = glue.encode_data("atac", atac)

print("RNA X_glue:", rna.obsm["X_glue"].shape)
print("ATAC X_glue:", atac.obsm["X_glue"].shape)

print("Writing outputs...")
rna.write(outdir / "rna_full_glue.h5ad", compression="gzip")
atac.write(outdir / "atac_full_glue.h5ad", compression="gzip")
nx.write_graphml(guidance, outdir / "guidance_full.graphml.gz")

if hasattr(glue, "save"):
    glue.save(outdir / "glue_full.dill")

print("Full GLUE run complete.")
print("Outputs written to:", outdir)
PY
