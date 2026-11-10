#!/bin/bash
#SBATCH --job-name=share_match_metrics
#SBATCH --time=24:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --array=0-17%3
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/matched_metrics_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/matched_metrics_%A_%a.err
set -euo pipefail
R=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020; E=/project/6001426/paa40/GlUE_Exp/GLUE/conda
set +u
eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate "$E"
set -u
hash -r
$E/bin/python "$R/scripts/matched_validate_run.py" "$SLURM_ARRAY_TASK_ID"
$E/bin/python "$R/scripts/matched_evaluate_one.py" "$SLURM_ARRAY_TASK_ID"
