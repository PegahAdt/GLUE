#!/usr/bin/env bash
#SBATCH --job-name=gat10x_tune
#SBATCH --time=2-00:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=192G
#SBATCH --gpus-per-node=h100:1

set -euo pipefail

BATCH_DIR="${1:?Batch directory argument is required}"

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL_DIR="$REPO/evaluation"

CONFIG_TABLE="$BATCH_DIR/configs.tsv"
EXPECTED_COMMIT=$(cat "$BATCH_DIR/base_commit.txt")

CURRENT_COMMIT=$(git -C "$REPO" rev-parse HEAD)

if [[ "$CURRENT_COMMIT" != "$EXPECTED_COMMIT" ]]; then
    echo "ERROR: Repository commit changed after setup."
    echo "Expected: $EXPECTED_COMMIT"
    echo "Current:  $CURRENT_COMMIT"
    echo
    echo "This job is stopping to avoid running a different model."
    exit 1
fi

LINE_NUMBER=$((SLURM_ARRAY_TASK_ID + 2))

CONFIG_LINE=$(
    awk -F $'\t' \
        -v line_number="$LINE_NUMBER" \
        'NR == line_number { print; exit }' \
        "$CONFIG_TABLE"
)

if [[ -z "$CONFIG_LINE" ]]; then
    echo "ERROR: No configuration for array index:"
    echo "  $SLURM_ARRAY_TASK_ID"
    exit 1
fi

IFS=$'\t' read -r \
    CONFIG_NAME \
    LEARNING_RATE \
    LAM_GRAPH \
    LAM_ALIGN \
    NEGATIVE_SLOPE \
    <<< "$CONFIG_LINE"

CONFIG_DIR="$BATCH_DIR/configs/$CONFIG_NAME"
WORKFLOW="$CONFIG_DIR/workflow/Snakefile"
TARGET_FILE="$CONFIG_DIR/targets.txt"

if [[ ! -s "$TARGET_FILE" ]]; then
    echo "ERROR: Missing target file:"
    echo "  $TARGET_FILE"
    exit 1
fi

mapfile -t TARGETS < "$TARGET_FILE"

if [[ "${#TARGETS[@]}" -ne 10 ]]; then
    echo "ERROR: Expected 10 targets but found:"
    echo "  ${#TARGETS[@]}"
    exit 1
fi

echo "============================================================"
echo "GAT tuning configuration"
echo "============================================================"
echo "Slurm job:         ${SLURM_JOB_ID}"
echo "Array index:       ${SLURM_ARRAY_TASK_ID}"
echo "Configuration:     ${CONFIG_NAME}"
echo "Learning rate:     ${LEARNING_RATE}"
echo "lam_graph:         ${LAM_GRAPH}"
echo "lam_align:         ${LAM_ALIGN}"
echo "Negative slope:    ${NEGATIVE_SLOPE}"
echo "Repository commit: ${CURRENT_COMMIT}"
echo "Targets:           ${#TARGETS[@]}"
echo "Started:           $(date)"
echo "============================================================"

cat > "$CONFIG_DIR/job_${SLURM_JOB_ID}.txt" <<EOF
job_id=${SLURM_JOB_ID}
array_task_id=${SLURM_ARRAY_TASK_ID}
config_name=${CONFIG_NAME}
lr=${LEARNING_RATE}
lam_graph=${LAM_GRAPH}
lam_align=${LAM_ALIGN}
gat_negative_slope=${NEGATIVE_SLOPE}
commit=${CURRENT_COMMIT}
started=$(date)
EOF


# Activate the exact GLUE environment.
set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u

micromamba activate "$REPO/conda"
hash -r

unset PYTHONHOME || true
export PYTHONNOUSERSITE=1
export PYTHONPATH="$REPO"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo
echo "Python:"
which python

echo
echo "Snakemake:"
which snakemake

echo
echo "Imported scglue:"
python - <<'PY'
import scglue
print(scglue.__file__)
PY


# All configurations have isolated output roots, so separate
# Snakemake processes cannot overwrite one another.
cd "$EVAL_DIR"

snakemake \
    --snakefile "$WORKFLOW" \
    --cores "$SLURM_CPUS_PER_TASK" \
    --resources gpu=1 \
    --latency-wait 120 \
    --rerun-incomplete \
    --keep-going \
    --printshellcmds \
    --nolock \
    "${TARGETS[@]}"


# Final validation: every requested target must exist and be nonempty.
MISSING=0

for target in "${TARGETS[@]}"; do
    if [[ ! -s "$target" ]]; then
        echo "MISSING TARGET: $target"
        MISSING=$((MISSING + 1))
    fi
done

if [[ "$MISSING" -ne 0 ]]; then
    echo "ERROR: $MISSING requested targets are missing."
    exit 1
fi

touch "$CONFIG_DIR/COMPLETED"

cat >> "$CONFIG_DIR/job_${SLURM_JOB_ID}.txt" <<EOF
completed=$(date)
status=success
EOF

echo
echo "Configuration completed successfully:"
echo "  $CONFIG_NAME"
echo "Finished: $(date)"
