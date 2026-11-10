#!/bin/bash
#SBATCH --job-name=pbmc_gcn_smoke_cpu
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8
#SBATCH --chdir=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/logs/smoke_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/logs/smoke_%j.err
set -euo pipefail
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/environment.sh
export CUDA_VISIBLE_DEVICES=""
[[ -n "${SLURM_JOB_ID:-}" ]] || { echo 'Smoke training requires Slurm' >&2; exit 2; }
"$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/train.py" --smoke
"$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/evaluate.py" --mode smoke \
    --smoke-run "$GCN_EXPERIMENT/smoke/job_$SLURM_JOB_ID/run" \
    --output "$GCN_EXPERIMENT/smoke/job_$SLURM_JOB_ID/evaluation"
test -s "$GCN_EXPERIMENT/validation/smoke_success.json"
echo 'SMOKE PASSED: original GCN training, saved embeddings/checkpoints, gate-free evaluation and reporting on a CPU compute node.'
