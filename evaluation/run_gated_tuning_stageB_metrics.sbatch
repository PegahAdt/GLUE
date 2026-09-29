#!/bin/bash
#SBATCH --job-name=gated_tune_B_met
#SBATCH --time=24:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/gated_tune_B_met_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/gated_tune_B_met_%A_%a.err
set -euo pipefail
REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED
ENV_PREFIX=/project/6001426/paa40/GlUE_Exp/GLUE/conda
OLD_EVAL=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation
CFG=$REPO/evaluation/gated_tuning_stageB_configs.tsv
TASK_ID=${SLURM_ARRAY_TASK_ID:?}
row=$(awk -F '\t' -v id="$TASK_ID" 'NR>1 && $1==id {print; exit}' "$CFG"); test -n "$row"
IFS=$'\t' read -r task gate keep lam_graph size seed model_seed reuse <<< "$row"
tag="gate_init:${gate}-lam_keep:${keep}-lam_graph:${lam_graph}-size:${size}-subsample_seed:${seed}-model_seed:${model_seed}"
dest=$REPO/evaluation/results_gated_tuning/stageB/$tag; run=$dest
while test -s "$run/REUSED_FROM"; do run=$(cat "$run/REUSED_FROM"); done
for f in rna_latent.csv atac_latent.csv feature_latent.csv gate_diagnostics.yaml run_info.yaml; do test -s "$run/$f"; done
input=$OLD_EVAL/results_gcn_h100/raw/10x-Multiome-Pbmc10k/subsample_size:${size}-subsample_seed:${seed}
mkdir -p "$dest"
export PYTHONPATH="$REPO" PYTHONNOUSERSITE=1 LD_LIBRARY_PATH="$ENV_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK} MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK}
py=$ENV_PREFIX/bin/python; cd "$REPO/evaluation"
$py -u workflow/scripts/cell_integration.py -d "$input/rna.h5ad" "$input/atac.h5ad" \
 -l "$run/rna_latent.csv" "$run/atac_latent.csv" --cell-type cell_type --domain domain -p \
 -o "$dest/cell_integration.yaml" > "$dest/cell_integration.log" 2>&1
$py -u workflow/scripts/combine_metrics.py -i "$run/run_info.yaml" "$dest/cell_integration.yaml" \
 -o "$dest/metrics.yaml" > "$dest/combine_metrics.log" 2>&1
test -s "$dest/metrics.yaml"
