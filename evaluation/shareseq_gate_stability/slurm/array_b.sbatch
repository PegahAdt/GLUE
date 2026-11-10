#!/bin/bash
#SBATCH --job-name=share_gate_B
#SBATCH --account=def-chauvec_gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --gres=gpu:h100:1
#SBATCH --array=0-47
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/logs/array_B_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/logs/array_B_%A_%a.err
set -euo pipefail
date --iso-8601=seconds
hostname
printf 'SLURM_JOB_ID=%s SLURM_ARRAY_JOB_ID=%s SLURM_ARRAY_TASK_ID=%s\n' "$SLURM_JOB_ID" "$SLURM_ARRAY_JOB_ID" "$SLURM_ARRAY_TASK_ID"
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/environment.sh
command -v python
python --version
printf 'CONDA_PREFIX=%s PYTHONPATH=%s\n' "$CONDA_PREFIX" "$PYTHONPATH"
nvidia-smi
exec python -u experiment.py run B "$SLURM_ARRAY_TASK_ID"
