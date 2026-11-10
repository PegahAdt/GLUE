#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${1:?Slurm allocation job ID is required}"
REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
LOG="$REPO/logs/gat_manual_search_${JOB_ID}.log"

while true; do
    STATE=$(squeue -h -j "$JOB_ID" -o '%T')
    if [[ "$STATE" == "RUNNING" ]]; then
        break
    fi
    if [[ -z "$STATE" ]]; then
        echo "Allocation $JOB_ID disappeared before starting." >&2
        exit 1
    fi
    echo "$(date): allocation $JOB_ID is $STATE"
    sleep 30
done

echo "$(date): launching search in allocation $JOB_ID"
srun --jobid="$JOB_ID" \
    --ntasks=1 \
    --cpus-per-task=8 \
    bash "$REPO/evaluation/run_gat_manual_search_in_allocation.sh" \
    > "$LOG" 2>&1
echo "$(date): search finished; log: $LOG"
