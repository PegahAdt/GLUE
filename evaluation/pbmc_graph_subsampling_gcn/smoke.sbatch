#!/bin/bash
#SBATCH --job-name=pbmc_gcn_smoke
#SBATCH --time=00:45:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --chdir=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/logs/smoke_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/logs/smoke_%j.err
set -euo pipefail
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/environment.sh
[[ -n "${SLURM_JOB_ID:-}" ]] || { echo 'Smoke training requires Slurm' >&2; exit 2; }
"$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/train.py" --smoke
export CUDA_VISIBLE_DEVICES=""
"$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/evaluate.py" --mode smoke \
    --smoke-run "$GCN_EXPERIMENT/smoke/job_$SLURM_JOB_ID/run" \
    --output "$GCN_EXPERIMENT/smoke/job_$SLURM_JOB_ID/evaluation"
test -s "$GCN_EXPERIMENT/validation/smoke_success.json"
echo 'SMOKE PASSED: original GCN training, saved embeddings/checkpoints, gate-free evaluation and reporting.'
