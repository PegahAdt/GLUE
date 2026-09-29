#!/bin/bash
#SBATCH --job-name=gated_edges
#SBATCH --account=def-chauvec
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=evaluation/gate_analysis/slurm-%j.out

set -euo pipefail
cd /project/6001426/paa40/GlUE_Exp/GLUE_GATED
export PYTHONPATH=/project/6001426/paa40/GlUE_Exp/GLUE_GATED
export PYTHONNOUSERSITE=1
export MPLCONFIGDIR="${SLURM_TMPDIR}/matplotlib"
mkdir -p evaluation/gate_analysis "$MPLCONFIGDIR"
micromamba run -p /project/6001426/paa40/GlUE_Exp/GLUE/conda \
  python -u evaluation/extract_gated_edge_analysis.py
