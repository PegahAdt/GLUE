#!/bin/bash
#SBATCH --job-name=share_train
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=0-25%6
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/train_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/train_%A_%a.err
set -euo pipefail
bash /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/scripts/train_one.sh "$SLURM_ARRAY_TASK_ID"
