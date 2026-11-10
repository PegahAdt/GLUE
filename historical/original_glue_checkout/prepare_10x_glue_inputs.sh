#!/bin/bash
#SBATCH --job-name=prep_10x_glue
#SBATCH --time=4:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=prep_10x_glue_%j.out
#SBATCH --error=prep_10x_glue_%j.err

set -eo pipefail

cd /project/6001426/paa40/GLUE/GLUE

source activate_glue.sh

python - <<'PY'
import anndata as ad
import scanpy as sc
import scglue
import networkx as nx

rna_path = "data/dataset/10x-Multiome-Pbmc10k-RNA.h5ad"
atac_path = "data/dataset/10x-Multiome-Pbmc10k-ATAC.h5ad"

rna_out = "data/dataset/10x-Multiome-Pbmc10k-RNA-glue-ready.h5ad"
atac_out = "data/dataset/10x-Multiome-Pbmc10k-ATAC-glue-ready.h5ad"
graph_out = "data/dataset/10x-Multiome-Pbmc10k-guidance.graphml.gz"

print("Reading data...")
rna = ad.read_h5ad(rna_path)
atac = ad.read_h5ad(atac_path)

print("RNA:", rna.shape)
print("ATAC:", atac.shape)

print("Saving raw count matrices into layers['counts']...")
rna.layers["counts"] = rna.X.copy()
atac.layers["counts"] = atac.X.copy()

print("Preparing RNA PCA...")
# RNA already has highly_variable from official file.
if "highly_variable" not in rna.var:
    raise RuntimeError("RNA is missing highly_variable; expected 2000 HV genes.")

sc.pp.normalize_total(rna)
sc.pp.log1p(rna)
sc.pp.scale(rna, max_value=10)
sc.tl.pca(rna, n_comps=100, use_highly_variable=True, svd_solver="auto")

print("Preparing ATAC LSI...")
# ATAC has no highly_variable column in this file.
# For this first smoke-test path, keep all peaks.
atac.var["highly_variable"] = True
scglue.data.lsi(atac, n_components=100, n_iter=15)

print("Checking coordinate columns...")
for x, name in [(rna, "RNA"), (atac, "ATAC")]:
    missing = [c for c in ["chrom", "chromStart", "chromEnd"] if c not in x.var]
    if missing:
        raise RuntimeError(f"{name} missing coordinate columns: {missing}")

print("Building guidance graph...")
guidance = scglue.genomics.rna_anchored_prior_graph(rna, atac)
print("Guidance nodes:", guidance.number_of_nodes())
print("Guidance edges:", guidance.number_of_edges())

print("Writing outputs...")
rna.write(rna_out, compression="gzip")
atac.write(atac_out, compression="gzip")
nx.write_graphml(guidance, graph_out)

print("Wrote:", rna_out)
print("Wrote:", atac_out)
print("Wrote:", graph_out)

print("Final slots:")
print("RNA layers:", list(rna.layers.keys()))
print("RNA obsm:", list(rna.obsm.keys()))
print("ATAC layers:", list(atac.layers.keys()))
print("ATAC obsm:", list(atac.obsm.keys()))
PY
