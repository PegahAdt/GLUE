#!/bin/bash

cd /home/chauvec/project/paa40/GlUE_Exp/GLUE

export PATH="$HOME/bin:$PATH"
export MAMBA_ROOT_PREFIX="$HOME/.local/share/mamba"

eval "$(micromamba shell hook --shell bash)"
micromamba activate ./conda

unset PYTHONPATH
export PYTHONNOUSERSITE=1

echo "Activated GLUE environment at: $CONDA_PREFIX"
python --version
