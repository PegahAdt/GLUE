#!/bin/bash
#SBATCH --job-name=gat10x_cmp
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=1
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_cmp_corrected_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_cmp_corrected_%j.err

set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"

cd "$REPO"

# Micromamba's shell hook may inspect an unset variable.
set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u

micromamba activate "$REPO/conda"
hash -r

unset PYTHONPATH || true
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

cd "$REPO/evaluation"

python compare_10x_gat_vs_gcn.py \
    --gat-targets gat_10x_subsample_targets.txt \
    --gcn-targets gcn_10x_subsample_targets.txt \
    --benchmark results/benchmark.csv \
    --output-dir results_gat/comparison_10x
