#!/bin/bash
#SBATCH --job-name=share_rescue
#SBATCH --time=01:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/rescue_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/rescue_%j.err
set -euo pipefail
ROOT=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020
ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda
OUT=$ROOT/results/smoke_gated_500
set +u
eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate "$ENV"
set -u
export PYTHONPATH=/project/6001426/paa40/GlUE_Exp/GLUE_GATED PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8} MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
$ENV/bin/python "$ROOT/scripts/validate_smoke.py"
$ENV/bin/python "$ROOT/scripts/evaluate_one.py" --smoke "$OUT"
$ENV/bin/python "$ROOT/scripts/extract_gates.py" --smoke "$OUT"
$ENV/bin/python "$ROOT/scripts/validate_smoke.py"
test -s "$OUT/gates.csv"
test -s "$OUT/gate_summary.yaml"
printf 'Validated by job %s\n' "${SLURM_JOB_ID:-manual}" > "$OUT/SMOKE_OK"
