#!/bin/bash
#SBATCH --job-name=gated_10x_smoke
#SBATCH --time=01:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8
#SBATCH --output=evaluation/.slurm/gated_10x_smoke_%j.out
#SBATCH --error=evaluation/.slurm/gated_10x_smoke_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE_GATED

eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate /project/6001426/paa40/GlUE_Exp/GLUE/conda
hash -r

unset PYTHONPATH
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

branch="$(git branch --show-current)"
commit="$(git rev-parse --short HEAD)"

echo "Branch: $branch"
echo "Commit: $commit"
echo "Python: $(which python)"
echo "Started: $(date)"

if [ "$branch" != "GATED_GLUE_WIP_20260806_191324" ]; then
    echo "ERROR: Expected branch GATED_GLUE_WIP_20260806_191324, found $branch"
    exit 1
fi

export GATED_SMOKE_OUTDIR="evaluation/results_gated/smoke/${SLURM_JOB_ID}"
mkdir -p "$GATED_SMOKE_OUTDIR"

python -u - <<'PY'
import math
import os
from pathlib import Path

import anndata as ad
import networkx as nx
import numpy as np
import pandas as pd

import scglue
from scglue.utils import config


outdir = Path(os.environ["GATED_SMOKE_OUTDIR"])
rna_path = Path(
    "/project/6001426/paa40/GlUE_Exp/GLUE/results/10x_smoke/"
    "rna_smoke_glue.h5ad"
)
atac_path = Path(
    "/project/6001426/paa40/GlUE_Exp/GLUE/results/10x_smoke/"
    "atac_smoke_glue.h5ad"
)
graph_path = Path(
    "/project/6001426/paa40/GlUE_Exp/GLUE/results/10x_smoke/"
    "guidance_smoke.graphml.gz"
)

for path in (rna_path, atac_path, graph_path):
    if not path.is_file():
        raise FileNotFoundError(f"Required smoke input does not exist: {path}")

print("scglue source:", scglue.__file__)
print("Reading prepared real 10x Multiome PBMC smoke subset...")
rna = ad.read_h5ad(rna_path)
atac = ad.read_h5ad(atac_path)
guidance = nx.read_graphml(graph_path)

# The prepared files were written after an earlier smoke run.  Restore the
# ordinary pretraining configuration before estimating fresh balancing weights.
for dataset in (rna, atac):
    dataset.uns[config.ANNDATA_KEY]["use_dsc_weight"] = None

graph_edges = guidance.number_of_edges()
self_loops = nx.number_of_selfloops(guidance)
expected_gate_logits = graph_edges - self_loops
print("RNA data shape:", rna.shape)
print("ATAC data shape:", atac.shape)
print("Graph nodes:", guidance.number_of_nodes())
print("Graph directed edges:", graph_edges)
print("Graph self-loops:", self_loops)
print("Expected trainable gate logits:", expected_gate_logits)


def gate_summary(label, model):
    info = model.get_graph_gates()
    gates = info["gate"].detach().cpu().numpy()
    is_self_loop = info["is_self_loop"].detach().cpu().numpy()
    trainable_gates = gates[~is_self_loop]
    logits = model.net.g2v.gate_logits.detach().cpu().numpy().copy()
    actual_logits = logits.size
    if actual_logits != expected_gate_logits:
        raise RuntimeError(
            f"Expected {expected_gate_logits} gate logits, got {actual_logits}"
        )
    if not np.isfinite(gates).all() or not np.isfinite(logits).all():
        raise RuntimeError(f"{label} gates or logits contain non-finite values")
    if type(model.net.g2v).__name__ != "GatedGraphEncoder":
        raise RuntimeError(f"{label} model did not select GatedGraphEncoder")
    if not np.equal(gates[is_self_loop], 1.0).all():
        raise RuntimeError(f"{label} self-loop gates are not exactly one")
    print(f"{label} encoder class:", type(model.net.g2v).__name__)
    print(f"{label} trainable gate logits:", actual_logits)
    print(
        f"{label} activated non-self gate min/mean/max:",
        float(trainable_gates.min()),
        float(trainable_gates.mean()),
        float(trainable_gates.max())
    )
    print(f"{label} gates finite: True")
    return logits, gates


model_kws = {
    "graph_encoder": "gated",
    "gate_init": 0.95,
    "random_seed": 0,
}
compile_kws = {"lam_keep": 0.0}

print("Constructing and configuring gated pretraining model...")
pretrain = scglue.models.SCGLUEModel(
    {"rna": rna, "atac": atac}, sorted(guidance.nodes),
    shared_batches=False, **model_kws
)
pretrain.configure_graph_encoder(guidance)
initial_logits, initial_gates = gate_summary("Initial", pretrain)
expected_initial_logit = math.log(0.95 / 0.05)
if not np.allclose(initial_logits, expected_initial_logit):
    raise RuntimeError("Real-graph gate logits do not match gate_init=0.95")
if not np.allclose(initial_gates[initial_gates < 1.0], 0.95):
    raise RuntimeError("Initial activated non-self gates do not equal 0.95")
pretrain.compile(**compile_kws)
print("Pretraining compile complete; beginning two smoke epochs...")
pretrain.fit(
    {"rna": rna, "atac": atac}, guidance,
    align_burnin=np.inf, safe_burnin=False,
    max_epochs=2, directory=str(outdir / "fit" / "pretrain")
)
pretrain_path = outdir / "pretrain.dill"
pretrain.save(pretrain_path)
if not pretrain_path.is_file():
    raise RuntimeError("Pretraining model serialization did not create a file")
print("Pretraining complete.")

print("Estimating balancing weights for the real fine-tuning path...")
tmp_rep = f"X_{config.TMP_PREFIX}"
for key, dataset in (("rna", rna), ("atac", atac)):
    dataset.obsm[tmp_rep] = pretrain.encode_data(key, dataset)
scglue.data.estimate_balancing_weight(
    rna, atac, use_rep=tmp_rep, key_added="balancing_weight"
)
for dataset in (rna, atac):
    dataset.uns[config.ANNDATA_KEY]["use_dsc_weight"] = "balancing_weight"
    del dataset.obsm[tmp_rep]

print("Constructing and configuring gated fine-tuning model...")
finetune = scglue.models.SCGLUEModel(
    {"rna": rna, "atac": atac}, sorted(guidance.nodes), **model_kws
)
finetune.configure_graph_encoder(guidance)
finetune.adopt_pretrained_model(pretrain)
if not np.array_equal(
        finetune.net.g2v.gate_logits.detach().cpu().numpy(),
        pretrain.net.g2v.gate_logits.detach().cpu().numpy()):
    raise RuntimeError("Fine-tuning model did not adopt pretrained gate logits")
print("Gated pretrained adoption complete.")
finetune.compile(**compile_kws)
print("Fine-tuning compile complete; beginning two smoke epochs...")
finetune.fit(
    {"rna": rna, "atac": atac}, guidance,
    max_epochs=2, directory=str(outdir / "fit" / "fine-tune")
)
finetune_path = outdir / "fine-tune.dill"
finetune.save(finetune_path)
if not finetune_path.is_file():
    raise RuntimeError("Fine-tuning model serialization did not create a file")
print("Fine-tuning complete.")

final_logits, final_gates = gate_summary("Final", finetune)
max_logit_change = float(np.max(np.abs(final_logits - expected_initial_logit)))
logits_changed = not np.allclose(final_logits, expected_initial_logit)
print("Maximum absolute gate-logit change from initialization:", max_logit_change)
print("Gate logits changed from initialization:", logits_changed)
if not logits_changed:
    raise RuntimeError("Gate logits did not change from initialization")

print("Encoding cells and graph features...")
rna_embedding = finetune.encode_data("rna", rna)
atac_embedding = finetune.encode_data("atac", atac)
feature_embedding = finetune.encode_graph(guidance)

for name, embedding in (
        ("RNA", rna_embedding),
        ("ATAC", atac_embedding),
        ("Feature", feature_embedding)):
    finite = bool(np.isfinite(embedding).all())
    print(f"{name} embedding shape:", embedding.shape)
    print(f"{name} embedding finite:", finite)
    if not finite:
        raise RuntimeError(f"{name} embedding contains non-finite values")

pd.DataFrame(rna_embedding, index=rna.obs_names).to_csv(
    outdir / "rna_embedding.csv"
)
pd.DataFrame(atac_embedding, index=atac.obs_names).to_csv(
    outdir / "atac_embedding.csv"
)
pd.DataFrame(feature_embedding, index=finetune.vertices).to_csv(
    outdir / "feature_embedding.csv"
)
pd.DataFrame({
    "source": finetune.get_graph_gates()["source"].cpu().numpy(),
    "target": finetune.get_graph_gates()["target"].cpu().numpy(),
    "gate": final_gates,
}).to_csv(outdir / "gate_summary.csv", index=False)

print("Real-data GATED_GLUE smoke test passed.")
print("Outputs written to:", outdir)
PY

echo "Finished: $(date)"
echo "Output directory: $GATED_SMOKE_OUTDIR"
