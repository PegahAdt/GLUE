#!/bin/bash
#SBATCH --job-name=pbmc_gcn_combined
#SBATCH --time=06:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --chdir=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/logs/evaluate_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/logs/evaluate_%j.err
set -euo pipefail
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/environment.sh
GCN_EXPERIMENT="$GCN_EXPERIMENT/randomized_control"
export CUDA_VISIBLE_DEVICES=""
exec "$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/evaluate.py" --mode full \
    --output "$GCN_REPO/evaluation/pbmc_graph_subsampling_gcn/reports/combined_randomized_job_$SLURM_JOB_ID"
