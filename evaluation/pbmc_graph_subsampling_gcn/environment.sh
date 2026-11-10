#!/bin/bash
# Shared original-GLUE environment; source this from all experiment launchers.
GCN_REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
GCN_ORIGINAL=/project/6001426/paa40/GlUE_Exp/GLUE
GCN_EXPERIMENT="$GCN_REPO/evaluation/pbmc_graph_subsampling_gcn"
GCN_ENV="$GCN_ORIGINAL/conda"
export PATH="$GCN_ENV/bin:$PATH"
export PYTHONPATH="$GCN_ORIGINAL"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export LD_LIBRARY_PATH="$GCN_ENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
export MKL_NUM_THREADS="$OMP_NUM_THREADS"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS"
export NUMBA_NUM_THREADS="$OMP_NUM_THREADS"
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-/tmp}/pbmc_gcn_numba_${SLURM_JOB_ID:-$UID}"
export MPLCONFIGDIR="${SLURM_TMPDIR:-/tmp}/pbmc_gcn_mpl_${SLURM_JOB_ID:-$UID}"
cd "$GCN_REPO"
