#!/bin/bash
#SBATCH --job-name=gat_10x_smoke
#SBATCH --time=04:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/gat_10x_smoke_%j.out
#SBATCH --error=logs/gat_10x_smoke_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE

eval "$($HOME/bin/micromamba shell hook --shell bash)"
micromamba activate /project/6001426/paa40/GlUE_Exp/GLUE/conda
hash -r

unset PYTHONPATH
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

BRANCH="$(git branch --show-current)"
COMMIT="$(git rev-parse --short HEAD)"

echo "Branch: $BRANCH"
echo "Commit: $COMMIT"
echo "Python: $(which python)"
echo "Started: $(date)"

if [ "$BRANCH" != "GAT_GLUE" ]; then
    echo "ERROR: Expected branch GAT_GLUE, found $BRANCH"
    exit 1
fi

export OUTDIR="results/10x_gat_smoke_${SLURM_JOB_ID}"
mkdir -p "$OUTDIR"

python - <<'PY'
from itertools import chain
from pathlib import Path
import os

import anndata as ad
import networkx as nx
import numpy as np
import pandas as pd
import scglue


outdir = Path(os.environ["OUTDIR"])

rna_path = Path(
    "/project/6001426/paa40/GLUE/GLUE/data/dataset/10x-Multiome-Pbmc10k-RNA-glue-ready.h5ad"
)

atac_path = Path(
    "/project/6001426/paa40/GLUE/GLUE/data/dataset/10x-Multiome-Pbmc10k-ATAC-glue-ready.h5ad"
)

graph_path = Path(
    "/project/6001426/paa40/GLUE/GLUE/data/dataset/10x-Multiome-Pbmc10k-guidance.graphml.gz"
)

for path in [rna_path, atac_path, graph_path]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required input does not exist: {path}"
        )


print("scglue:", scglue.__version__)
print("scglue source:", scglue.__file__)
print("Reading real 10x Multiome PBMC data...")

rna = ad.read_h5ad(rna_path)
atac = ad.read_h5ad(atac_path)
guidance = nx.read_graphml(graph_path)

print("Original RNA:", rna.shape)
print("Original ATAC:", atac.shape)
print(
    "Original graph:",
    guidance.number_of_nodes(),
    "nodes,",
    guidance.number_of_edges(),
    "edges"
)


# Use the first 1,000 shared cells
n_cells = min(
    1000,
    rna.n_obs,
    atac.n_obs
)

common_cells = rna.obs_names.intersection(
    atac.obs_names
)

if len(common_cells) >= n_cells:
    keep_cells = common_cells[:n_cells]
    rna = rna[keep_cells].copy()
    atac = atac[keep_cells].copy()
else:
    rna = rna[:n_cells].copy()
    atac = atac[:n_cells].copy()


# Keep the real highly variable RNA features
if "highly_variable" not in rna.var:
    raise RuntimeError(
        "RNA dataset does not contain highly_variable."
    )

rna = rna[
    :,
    rna.var["highly_variable"].to_numpy()
].copy()


# Keep up to 5,000 real ATAC peaks connected to RNA genes
gene_nodes = set(rna.var_names).intersection(
    guidance.nodes
)

peak_nodes = set(atac.var_names).intersection(
    guidance.nodes
)

connected_peaks = []

for source, target in guidance.edges():
    if source in gene_nodes and target in peak_nodes:
        connected_peaks.append(target)
    elif target in gene_nodes and source in peak_nodes:
        connected_peaks.append(source)

connected_peaks = list(
    dict.fromkeys(connected_peaks)
)

if not connected_peaks:
    raise RuntimeError(
        "No connected ATAC peaks were found."
    )

atac = atac[
    :,
    connected_peaks[:5000]
].copy()

atac.var["highly_variable"] = True


# Restrict the guidance graph to selected real features
features = list(
    chain(
        rna.var_names,
        atac.var_names
    )
)

guidance = guidance.subgraph(
    features
).copy()


print("Smoke RNA:", rna.shape)
print("Smoke ATAC:", atac.shape)
print(
    "Smoke graph:",
    guidance.number_of_nodes(),
    "nodes,",
    guidance.number_of_edges(),
    "edges"
)


# Confirm all GAT prior weights are valid
weights = np.asarray([
    float(data["weight"])
    for _, _, data in guidance.edges(data=True)
])

signs = np.asarray([
    float(data["sign"])
    for _, _, data in guidance.edges(data=True)
])

if not np.all(np.isfinite(weights)):
    raise RuntimeError(
        "Guidance graph contains non-finite weights."
    )

if not np.all(weights > 0):
    raise RuntimeError(
        "GAT requires every real edge weight to be positive."
    )

if not np.all(np.isin(signs, [-1.0, 1.0])):
    raise RuntimeError(
        "Guidance graph signs must be +1 or -1."
    )

print(
    "Weight range:",
    float(weights.min()),
    "to",
    float(weights.max())
)

print(
    "Positive edges:",
    int(np.sum(signs == 1))
)

print(
    "Negative edges:",
    int(np.sum(signs == -1))
)


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


print("Training real-data GAT smoke model...")

glue = scglue.models.fit_SCGLUE(
    {
        "rna": rna,
        "atac": atac
    },
    guidance,
    init_kws={
        "graph_encoder": "gat",
        "gat_negative_slope": 0.2,
        "random_seed": 0
    },
    fit_kws={
        "directory": str(outdir / "fit"),
        "max_epochs": 2
    }
)


encoder_type = type(
    glue.net.g2v
).__name__

print("Final encoder type:", encoder_type)

if encoder_type != "GATGraphEncoder":
    raise RuntimeError(
        "The trained model did not use GATGraphEncoder."
    )


print("Encoding cells and graph features...")

rna_embedding = glue.encode_data(
    "rna",
    rna
)

atac_embedding = glue.encode_data(
    "atac",
    atac
)

feature_embedding = glue.encode_graph(
    guidance,
    edge_weight="weight",
    edge_sign="sign"
)


for name, embedding in [
    ("RNA", rna_embedding),
    ("ATAC", atac_embedding),
    ("Feature", feature_embedding)
]:
    print(
        f"{name} embedding shape:",
        embedding.shape
    )

    if not np.isfinite(embedding).all():
        raise RuntimeError(
            f"{name} embedding contains non-finite values."
        )


rna.obsm["X_glue_gat"] = rna_embedding
atac.obsm["X_glue_gat"] = atac_embedding

rna.write(
    outdir / "rna_gat_smoke.h5ad",
    compression="gzip"
)

atac.write(
    outdir / "atac_gat_smoke.h5ad",
    compression="gzip"
)

pd.DataFrame(
    feature_embedding,
    index=glue.vertices
).to_csv(
    outdir / "feature_gat_smoke.csv"
)

nx.write_graphml(
    guidance,
    outdir / "guidance_gat_smoke.graphml.gz"
)

glue.save(
    outdir / "gat_smoke_model.dill"
)

print("Real-data GAT smoke test passed.")
print("Outputs written to:", outdir)
PY

echo "Finished: $(date)"
echo "Output directory: $OUTDIR"
