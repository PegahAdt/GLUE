#!/bin/bash
#SBATCH --job-name=share_metrics
#SBATCH --time=24:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --array=0-25%6
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/metrics_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/metrics_%A_%a.err
set -euo pipefail
R=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020; E=/project/6001426/paa40/GlUE_Exp/GLUE/conda
set +u
eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate "$E"
set -u
hash -r
$E/bin/python "$R/scripts/validate_run.py" "$SLURM_ARRAY_TASK_ID"
$E/bin/python "$R/scripts/evaluate_one.py" "$SLURM_ARRAY_TASK_ID"
eval "$($E/bin/python "$R/scripts/read_manifest.py" "$SLURM_ARRAY_TASK_ID" shell)"
if [[ "$architecture" == gated ]]; then PYTHONPATH=/project/6001426/paa40/GlUE_Exp/GLUE_GATED PYTHONNOUSERSITE=1 $E/bin/python "$R/scripts/extract_gates.py" "$SLURM_ARRAY_TASK_ID"; fi
