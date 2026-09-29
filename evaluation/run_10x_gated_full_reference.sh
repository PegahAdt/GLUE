#!/bin/bash
#SBATCH --job-name=gated10x_ref
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/gated10x_ref_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/gated10x_ref_%j.err

set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE_GATED"
OLD_EVAL="/project/6001426/paa40/GlUE_Exp/GLUE/evaluation"
DATASET="10x-Multiome-Pbmc10k"
PRIOR="gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0"
HP="dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10"
INPUT_DIR="$OLD_EVAL/results_gcn_h100/raw/$DATASET/original"
DATA_DIR="$REPO/evaluation/results_gated/raw/$DATASET/original"
PRIOR_DIR="$DATA_DIR/$PRIOR"
RUN_DIR="$PRIOR_DIR/GLUE/$HP/seed:0"
TARGET="$RUN_DIR/feature_latent.csv"

echo "data=full model_seed=0 architecture=gated input=$INPUT_DIR result=$RUN_DIR"
echo "target=$TARGET"
if [[ "${DRY_RUN:-0}" == 1 ]]; then
    exit 0
fi

[[ "$(git -C "$REPO" branch --show-current)" == GATED_GLUE ]]
for file in rna.h5ad atac.h5ad frags2rna.h5ad; do
    test -s "$INPUT_DIR/$file"
done
test -s "$INPUT_DIR/$PRIOR/sub.graphml.gz"

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u
micromamba activate /project/6001426/paa40/GlUE_Exp/GLUE/conda
hash -r
export PYTHONPATH="$REPO"
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

mkdir -p "$DATA_DIR" "$PRIOR_DIR" "$RUN_DIR"
for file in rna.h5ad atac.h5ad frags2rna.h5ad; do
    ln -sfn "$INPUT_DIR/$file" "$DATA_DIR/$file"
done
ln -sfn "$INPUT_DIR/$PRIOR/sub.graphml.gz" "$PRIOR_DIR/sub.graphml.gz"

cd "$REPO/evaluation"
python -u workflow/scripts/run_GLUE.py \
    --input-rna "$DATA_DIR/rna.h5ad" --input-atac "$DATA_DIR/atac.h5ad" \
    --prior "$PRIOR_DIR/sub.graphml.gz" --dim 50 --alt-dim 100 \
    --hidden-depth 2 --hidden-dim 256 --dropout 0.2 \
    --lam-graph 0.02 --lam-align 0.05 --lr 0.002 --neg-samples 10 \
    --data-batch-size 128 \
    --graph-encoder gated --gate-init 0.95 --lam-keep 0.0 \
    --random-seed 0 --train-dir "$RUN_DIR" --random-sleep --require-converge \
    --output-rna "$RUN_DIR/rna_latent.csv" \
    --output-atac "$RUN_DIR/atac_latent.csv" \
    --output-feature "$TARGET" \
    --run-info "$RUN_DIR/run_info.yaml" > "$RUN_DIR/run_GLUE.log" 2>&1

test -s "$RUN_DIR/rna_latent.csv"
test -s "$RUN_DIR/atac_latent.csv"
test -s "$TARGET"
test ! -L "$TARGET"
test -s "$RUN_DIR/run_info.yaml"
test -s "$RUN_DIR/final.dill"
test -s "$RUN_DIR/gate_diagnostics.yaml"
echo "Full GATED reference completed: $TARGET"
