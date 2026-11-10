#!/bin/bash
#SBATCH --job-name=gat10x_sub
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=0-47
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_sub_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_sub_%A_%a.err

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

LINE_NUMBER=$((SLURM_ARRAY_TASK_ID + 1))

TARGET="$(
    sed -n "${LINE_NUMBER}p" \
    gat_10x_subsample_targets.txt
)"

if [ -z "$TARGET" ]; then
    echo "ERROR: No target for array task $SLURM_ARRAY_TASK_ID."
    exit 1
fi

echo "Array job: $SLURM_ARRAY_JOB_ID"
echo "Array task: $SLURM_ARRAY_TASK_ID"
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

echo "Completed:"
echo "$TARGET"
echo "Finished: $(date)"
