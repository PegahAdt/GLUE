#!/bin/bash
#SBATCH --job-name=share_dim_smoke
#SBATCH --chdir=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020
#SBATCH --time=02:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=11,23,35
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/dimension_smoke_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/dimension_smoke_%A_%a.err
set -euo pipefail
bash /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/scripts/full_dimension_smoke_one.sh "$SLURM_ARRAY_TASK_ID"
