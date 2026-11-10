#!/bin/bash
#SBATCH --job-name=glue10x_250
#SBATCH --time=2:50:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --array=0-7%4
#SBATCH --output=../logs/glue10x_250_%A_%a.out
#SBATCH --error=../logs/glue10x_250_%A_%a.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
source Run_On_fir/activate_glue.sh

cd /project/6001426/paa40/GlUE_Exp/GLUE/evaluation

TARGET=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" glue_10x_size250_targets.txt)

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
  --nolock \
  "$TARGET"

date
echo "Done: $TARGET"
