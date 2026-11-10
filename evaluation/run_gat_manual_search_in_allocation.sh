#!/usr/bin/env bash
set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"

cd "$REPO"
set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u
micromamba activate "$REPO/conda"
hash -r

unset PYTHONHOME || true
export PYTHONNOUSERSITE=1
export PYTHONPATH="$REPO"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

nvidia-smi
python -u evaluation/run_gat_manual_search.py
