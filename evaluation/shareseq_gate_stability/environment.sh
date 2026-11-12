#!/bin/bash
set -euo pipefail
STABILITY_REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED
STABILITY_ROOT=$STABILITY_REPO/evaluation/shareseq_gate_stability
STABILITY_ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda
cd "$STABILITY_ROOT"
set +u
eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate "$STABILITY_ENV"
set -u
hash -r
export PYTHONPATH="$STABILITY_REPO" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4} MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
export MKL_THREADING_LAYER=GNU
unset DIMENSION_SMOKE
