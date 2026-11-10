#!/bin/bash
#SBATCH --job-name=glue_env
#SBATCH --time=6:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --output=glue_env_%j.out
#SBATCH --error=glue_env_%j.err

set -eo pipefail

cd /project/6001426/paa40/GLUE/GLUE

export PATH="$HOME/bin:$PATH"
export MAMBA_ROOT_PREFIX="$HOME/.local/share/mamba"
mkdir -p "$MAMBA_ROOT_PREFIX"

eval "$(micromamba shell hook --shell bash)"

unset PYTHONPATH || true
export PYTHONNOUSERSITE=1

unset PIP_CONFIG_FILE || true
unset PIP_FIND_LINKS || true
unset PIP_NO_INDEX || true
unset PIP_INDEX_URL || true
unset PIP_EXTRA_INDEX_URL || true

rm -rf ./conda

micromamba create -y -p ./conda -f env.conda-only.yaml
micromamba activate ./conda

python --version
snakemake --version

if ! command -v flit >/dev/null 2>&1; then
    python -m pip install flit
fi

flit install -s

python - <<'PY'
import scglue
import torch
import scanpy
import anndata
import numpy
import pandas

print("scglue:", scglue.__version__, scglue.__file__)
print("torch:", torch.__version__)
print("scanpy:", scanpy.__version__)
print("anndata:", anndata.__version__)
print("numpy:", numpy.__version__)
print("pandas:", pandas.__version__)
PY
