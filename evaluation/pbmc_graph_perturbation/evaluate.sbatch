#!/bin/bash
#SBATCH --job-name=pbmc_graph_eval
#SBATCH --time=06:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --chdir=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_perturbation/logs/evaluate_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_perturbation/logs/evaluate_%j.err

set -euo pipefail
REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
GLUE_ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda
MODE=${1:-full}
case "$MODE" in full|preflight|smoke|test|report) ;; *) echo 'Mode must be full, preflight, smoke, test or report' >&2; exit 2;; esac
if [[ "$MODE" == full && -z "${SLURM_JOB_ID:-}" ]]; then
    echo 'Full evaluation requires a Slurm allocation. Use sbatch evaluate.sbatch.' >&2
    exit 2
fi
export PATH="$GLUE_ENV/bin:$PATH"
export PYTHONPATH="$REPO"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export LD_LIBRARY_PATH="$GLUE_ENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
export MKL_NUM_THREADS="$OMP_NUM_THREADS"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS"
export NUMBA_NUM_THREADS="$OMP_NUM_THREADS"
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-/tmp}/pbmc_evaluation_numba_${SLURM_JOB_ID:-$UID}"
export MPLCONFIGDIR="${SLURM_TMPDIR:-/tmp}/pbmc_evaluation_mpl_${SLURM_JOB_ID:-$UID}"
cd "$REPO"
if [[ "$MODE" == test ]]; then
    export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
    exec "$GLUE_ENV/bin/python" -B -m pytest tests/test_pbmc_evaluation.py -q
fi
DEST_MODE="$MODE"
[[ "$MODE" != report ]] || DEST_MODE=full
OUTPUT=${PBMC_EVAL_OUTPUT:-"$REPO/evaluation/pbmc_graph_perturbation/reports/$DEST_MODE"}
exec "$GLUE_ENV/bin/python" -B -u evaluation/pbmc_graph_perturbation/scripts/evaluate.py \
    --mode "$MODE" --output "$OUTPUT"
