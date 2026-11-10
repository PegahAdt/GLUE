#!/bin/bash
#SBATCH --job-name=glue_collect_one
#SBATCH --time=4:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --output=glue_collect_one_%j.out
#SBATCH --error=glue_collect_one_%j.err

set -eo pipefail

cd /project/6001426/paa40/GLUE/GLUE/data

export PATH="$HOME/bin:$PATH"
export MAMBA_ROOT_PREFIX="$HOME/.local/share/mamba"
eval "$(micromamba shell hook --shell bash)"
micromamba activate ../conda

unset PYTHONPATH
export PYTHONNOUSERSITE=1

echo "Node: $(hostname)"
echo "Started: $(date)"
python --version
snakemake --version

snakemake -j1 -pr collect/10x-Multiome-Pbmc10k.html

echo "Finished: $(date)"
