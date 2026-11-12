#!/bin/bash
#SBATCH --job-name=gated_tune_A
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=0-14
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/gated_tune_A_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/gated_tune_A_%A_%a.err
set -euo pipefail
REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED
ENV_PREFIX=/project/6001426/paa40/GlUE_Exp/GLUE/conda
OLD_EVAL=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation
CFG=$REPO/evaluation/gated_tuning_stageA_configs.tsv
TASK_ID=${SLURM_ARRAY_TASK_ID:?}
row=$(awk -F '\t' -v id="$TASK_ID" 'NR>1 && $1==id {print; exit}' "$CFG")
test -n "$row"
IFS=$'\t' read -r task gate keep size seed model_seed <<< "$row"
tag="gate_init:${gate}-lam_keep:${keep}-lam_graph:0.02-size:${size}-subsample_seed:${seed}-model_seed:${model_seed}"
run=$REPO/evaluation/results_gated_tuning/stageA/$tag
if [[ "$gate" == 0.95 && "$keep" == 0 ]]; then
  echo "Exact matched baseline is reused; no training is performed."
  mkdir -p "$run"
  printf '%s\n' "$REPO/evaluation/results_gated/raw/10x-Multiome-Pbmc10k/subsample_size:2000-subsample_seed:0/gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/GLUE/dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10/seed:0" > "$run/REUSED_FROM"
  exit 0
fi
input=$OLD_EVAL/results_gcn_h100/raw/10x-Multiome-Pbmc10k/subsample_size:${size}-subsample_seed:${seed}
prior=$input/gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/sub.graphml.gz
mkdir -p "$run"
export PYTHONPATH="$REPO" PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$ENV_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK} MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK}
py=$ENV_PREFIX/bin/python
resolved=$($py -c 'import pathlib,scglue; print(pathlib.Path(scglue.__file__).resolve())')
[[ "$resolved" == "$REPO"/scglue/* ]] || { echo "Wrong scglue: $resolved" >&2; exit 3; }
$py -u "$REPO/evaluation/validate_10x_gated_subsamples.py" --size "$size" --seed "$seed"
cd "$REPO/evaluation"
$py -u workflow/scripts/run_GLUE.py \
 --input-rna "$input/rna.h5ad" --input-atac "$input/atac.h5ad" --prior "$prior" \
 --dim 50 --alt-dim 100 --hidden-depth 2 --hidden-dim 256 --dropout 0.2 \
 --lam-graph 0.02 --lam-align 0.05 --lr 0.002 --neg-samples 10 --data-batch-size 128 \
 --graph-encoder gated --gate-init "$gate" --lam-keep "$keep" --random-seed "$model_seed" \
 --train-dir "$run" --random-sleep --require-converge \
 --output-rna "$run/rna_latent.csv" --output-atac "$run/atac_latent.csv" \
 --output-feature "$run/feature_latent.csv" --run-info "$run/run_info.yaml" > "$run/run_GLUE.log" 2>&1
for f in rna_latent.csv atac_latent.csv feature_latent.csv gate_diagnostics.yaml run_info.yaml final.dill; do test -s "$run/$f"; done
