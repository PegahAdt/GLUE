#!/bin/bash
#SBATCH --job-name=smoke_10x_glue
#SBATCH --time=4:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/smoke_10x_glue_%j.out
#SBATCH --error=logs/smoke_10x_glue_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
mkdir -p logs results/10x_smoke

source /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/activate_glue.sh

python - <<'PY'
from pathlib import Path
import anndata as ad
import scanpy as sc
import scglue
import networkx as nx
import numpy as np

outdir = Path("results/10x_smoke")
outdir.mkdir(parents=True, exist_ok=True)

print("Reading 10x Multiome data...")
rna = ad.read_h5ad("data/dataset/10x-Multiome-Pbmc10k-RNA.h5ad")
atac = ad.read_h5ad("data/dataset/10x-Multiome-Pbmc10k-ATAC.h5ad")

print("Full RNA:", rna.shape)
print("Full ATAC:", atac.shape)

print("Subsetting cells...")
common = rna.obs_names.intersection(atac.obs_names)

if len(common) >= 1000:
    keep_cells = common[:1000]
    rna = rna[keep_cells].copy()
    atac = atac[keep_cells].copy()
else:
    n = min(1000, rna.n_obs, atac.n_obs)
    rna = rna[:n].copy()
    atac = atac[:n].copy()

print("Smoke RNA:", rna.shape)
print("Smoke ATAC:", atac.shape)

print("Saving raw count layers...")
rna.layers["counts"] = rna.X.copy()
atac.layers["counts"] = atac.X.copy()

print("Preprocessing RNA...")
sc.pp.normalize_total(rna)
sc.pp.log1p(rna)

if "highly_variable" not in rna.var:
    sc.pp.highly_variable_genes(rna, n_top_genes=2000, flavor="seurat")

sc.pp.scale(rna, max_value=10)
sc.tl.pca(rna, n_comps=50, use_highly_variable=True, svd_solver="auto")

print("Preprocessing ATAC...")
atac.var["highly_variable"] = True
scglue.data.lsi(atac, n_components=50, n_iter=15)

print("Building guidance graph...")
guidance = scglue.genomics.rna_anchored_prior_graph(rna, atac)

print("Initial guidance graph:")
print("  nodes:", guidance.number_of_nodes())
print("  edges:", guidance.number_of_edges())

print("Reducing to smoke-test feature set...")

rna_hvg = rna.var_names[rna.var["highly_variable"].to_numpy()]
rna = rna[:, rna_hvg].copy()

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
    raise RuntimeError("No connected ATAC peaks found in guidance graph")

connected_peaks = connected_peaks[:5000]
atac = atac[:, connected_peaks].copy()
atac.var["highly_variable"] = True

features = list(rna.var_names) + list(atac.var_names)
guidance = guidance.subgraph(features).copy()

print("Reduced smoke RNA:", rna.shape)
print("Reduced smoke ATAC:", atac.shape)
print("Reduced guidance graph:")
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

print("Training smoke-test GLUE model...")
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

print("Writing outputs...")
rna.write(outdir / "rna_smoke_glue.h5ad", compression="gzip")
atac.write(outdir / "atac_smoke_glue.h5ad", compression="gzip")
nx.write_graphml(guidance, outdir / "guidance_smoke.graphml.gz")

if hasattr(glue, "save"):
    glue.save(outdir / "glue_smoke.dill")

print("Smoke test complete.")
print("Outputs written to:", outdir)
PY
