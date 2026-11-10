#!/bin/bash
#SBATCH --job-name=pbmc_gcn_random
#SBATCH --time=06:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=0-2%3
#SBATCH --chdir=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/logs/train_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/logs/train_%A_%a.err
set -euo pipefail
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/environment.sh
[[ -n "${SLURM_JOB_ID:-}" && "${SLURM_ARRAY_TASK_ID:-}" =~ ^[0-2]$ ]] || {
    echo 'Training requires a Slurm array task 0..2' >&2; exit 2;
}
exec "$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/randomized_control/scripts/train.py" --task-id "$SLURM_ARRAY_TASK_ID"
