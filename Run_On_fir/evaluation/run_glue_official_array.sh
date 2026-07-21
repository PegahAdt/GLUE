#!/bin/bash
#SBATCH --job-name=glue_official_eval
#SBATCH --time=48:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=8
#SBATCH --array=0-239%4
#SBATCH --output=logs/glue_official_eval_%A_%a.out
#SBATCH --error=logs/glue_official_eval_%A_%a.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
source /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/activate_glue.sh

cd /project/6001426/paa40/GlUE_Exp/GLUE/evaluation
cp /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/evaluation/glue_official_targets.txt glue_official_targets.txt 2>/dev/null || true
cp /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/evaluation/glue_targets_250_500.txt glue_targets_250_500.txt 2>/dev/null || true

TARGET=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" glue_official_targets.txt)

echo "Array task: $SLURM_ARRAY_TASK_ID"
echo "Target: $TARGET"
date

snakemake \
  -s workflow/Snakefile \
  --configfile config/config.yaml \
  -j1 \
  --printshellcmds \
  --rerun-incomplete \
  --latency-wait 60 \
  "$TARGET"

date
echo "Done: $TARGET"
