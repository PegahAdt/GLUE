#!/bin/bash
#SBATCH --job-name=gated10x_metrics
#SBATCH --time=24:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/gated10x_metrics_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/gated10x_metrics_%j.err

set -euo pipefail
REPO="/project/6001426/paa40/GlUE_Exp/GLUE_GATED"
set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u
micromamba activate /project/6001426/paa40/GlUE_Exp/GLUE/conda
hash -r
unset PYTHONPATH || true
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
cd "$REPO"
bash evaluation/collect_10x_gated_metrics.sh
