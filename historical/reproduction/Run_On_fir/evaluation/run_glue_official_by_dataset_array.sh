#!/bin/bash
#SBATCH --job-name=glue_eval_ds
#SBATCH --time=11:30:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=8
#SBATCH --array=0-4%5
#SBATCH --output=logs/glue_eval_ds_%A_%a.out
#SBATCH --error=logs/glue_eval_ds_%A_%a.err

set -eo pipefail

DATASETS=(
  "Chen-2019"
  "Ma-2020"
  "10x-Multiome-Pbmc10k"
  "Muto-2021"
  "Yao-2021"
)

DATASET="${DATASETS[$SLURM_ARRAY_TASK_ID]}"

cd /project/6001426/paa40/GlUE_Exp/GLUE
source /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/activate_glue.sh

cd /project/6001426/paa40/GlUE_Exp/GLUE/evaluation
cp /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/evaluation/glue_official_targets.txt glue_official_targets.txt 2>/dev/null || true
cp /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/evaluation/glue_targets_250_500.txt glue_targets_250_500.txt 2>/dev/null || true

echo "Array task: $SLURM_ARRAY_TASK_ID"
echo "Dataset: $DATASET"
date

mapfile -t TARGETS < <(grep "^results/raw/${DATASET}/" glue_official_targets.txt)

echo "Number of targets for $DATASET: ${#TARGETS[@]}"
printf '%s\n' "${TARGETS[@]}"

snakemake \
  -s workflow/Snakefile \
  --configfile config/config.yaml \
  -j1 \
  --printshellcmds \
  --rerun-incomplete \
  --latency-wait 60 \
  --keep-going \
  --nolock \
  "${TARGETS[@]}"

date
echo "Done dataset: $DATASET"
