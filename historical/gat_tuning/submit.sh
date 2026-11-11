#!/usr/bin/env bash
set -euo pipefail

BATCH_DIR=$(cd "$(dirname "$0")" && pwd)

CONFIG_TABLE="$BATCH_DIR/configs.tsv"
LOG_DIR="$BATCH_DIR/logs"

mkdir -p "$LOG_DIR"

CONFIG_COUNT=$(
    tail -n +2 "$CONFIG_TABLE" \
    | awk 'NF { count += 1 } END { print count + 0 }'
)

if [[ "$CONFIG_COUNT" -le 0 ]]; then
    echo "ERROR: No configurations found."
    exit 1
fi

# At most two configuration jobs use H100 GPUs simultaneously.
MAX_CONCURRENT="${MAX_CONCURRENT:-2}"

ARRAY_END=$((CONFIG_COUNT - 1))

SUBMISSION=$(
    sbatch \
        --parsable \
        --array="0-${ARRAY_END}%${MAX_CONCURRENT}" \
        --output="$LOG_DIR/%A_%a.out" \
        --error="$LOG_DIR/%A_%a.err" \
        "$BATCH_DIR/run_one_config.sbatch" \
        "$BATCH_DIR"
)

JOB_ID="${SUBMISSION%%;*}"

cat > "$BATCH_DIR/submitted_job.txt" <<EOF
job_id=${JOB_ID}
array=0-${ARRAY_END}%${MAX_CONCURRENT}
config_count=${CONFIG_COUNT}
submitted=$(date)
EOF

echo "Submitted tuning array:"
echo "  Job ID:          $JOB_ID"
echo "  Configurations:  $CONFIG_COUNT"
echo "  Max concurrent:  $MAX_CONCURRENT"
echo
echo "Monitor with:"
echo "  squeue -j $JOB_ID"
