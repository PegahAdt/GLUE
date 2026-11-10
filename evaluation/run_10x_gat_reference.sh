#!/bin/bash
#SBATCH --job-name=gat10x_ref
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_ref_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_ref_%j.err

set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL="$REPO/evaluation"

cd "$REPO"

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u
micromamba activate "$REPO/conda"
hash -r

unset PYTHONPATH || true
export PYTHONNOUSERSITE=1

export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

cd "$EVAL"

TARGET="$(cat gat_10x_reference_target.txt)"

if [ -z "$TARGET" ]; then
    echo "ERROR: Empty reference target."
    exit 1
fi

echo "Job: $SLURM_JOB_ID"
echo "Branch: $(git -C "$REPO" branch --show-current)"
echo "Commit: $(git -C "$REPO" rev-parse --short HEAD)"
echo "Target: $TARGET"
echo "Started: $(date)"

snakemake \
    -s workflow_gat_10x/Snakefile \
    --configfile config/config.yaml \
    -j1 \
    --printshellcmds \
    --rerun-incomplete \
    --latency-wait 120 \
    --nolock \
    "$TARGET"

test -s "$TARGET"

echo "Reference completed:"
echo "$TARGET"
echo "Finished: $(date)"
