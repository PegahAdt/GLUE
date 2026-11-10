#!/bin/bash
#SBATCH --job-name=glue_10x_250
#SBATCH --time=2:50:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --output=../logs/glue_10x_250_%j.out
#SBATCH --error=../logs/glue_10x_250_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
source Run_On_fir/activate_glue.sh

cd /project/6001426/paa40/GlUE_Exp/GLUE/evaluation

TARGET=$(sed -n '1p' glue_10x_targets.txt)

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
echo "Done."
