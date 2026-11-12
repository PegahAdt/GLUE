#!/bin/bash
#SBATCH --job-name=pbmc_gcn_eval
#SBATCH --time=06:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --chdir=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/logs/evaluate_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/logs/evaluate_%j.err
set -euo pipefail
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/environment.sh
export CUDA_VISIBLE_DEVICES=""
exec "$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/evaluate.py" --mode full \
    --output "${PBMC_GCN_EVAL_OUTPUT:-$GCN_EXPERIMENT/reports/full}"
