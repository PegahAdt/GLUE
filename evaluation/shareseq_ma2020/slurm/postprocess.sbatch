#!/bin/bash
#SBATCH --job-name=share_report
#SBATCH --time=04:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/report_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/report_%j.err
set -euo pipefail
set +u
eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate /project/6001426/paa40/GlUE_Exp/GLUE/conda
set -u
hash -r
/project/6001426/paa40/GlUE_Exp/GLUE/conda/bin/python /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/scripts/postprocess.py
