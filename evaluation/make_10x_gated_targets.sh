#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

PRIOR="gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0"
HP="dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10"
TARGETS="gated_10x_subsample_targets.txt"

: > "$TARGETS"
for SIZE in 250 2000 8000; do
    for SEED in 0 1 2; do
        echo "results_gated/raw/10x-Multiome-Pbmc10k/subsample_size:${SIZE}-subsample_seed:${SEED}/${PRIOR}/GLUE/${HP}/seed:0/metrics.yaml" >> "$TARGETS"
    done
done

test "$(wc -l < "$TARGETS")" -eq 9
test "$(sed -E 's/.*subsample_size:([0-9]+)-subsample_seed:([0-9]+).*/\1 \2/' "$TARGETS" | sort -u | wc -l)" -eq 9
echo "Validated 9 unique GATED size/seed targets in $TARGETS"
