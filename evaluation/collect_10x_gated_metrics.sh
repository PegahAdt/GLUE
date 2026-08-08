#!/bin/bash
set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE_GATED"
OLD="/project/6001426/paa40/GlUE_Exp/GLUE/evaluation"
cd "$REPO/evaluation"

bash make_10x_gated_targets.sh

REFERENCE_REL="10x-Multiome-Pbmc10k/original/gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/GLUE/dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10/seed:0/feature_latent.csv"
GATED_REFERENCE="results_gated/raw/$REFERENCE_REL"
test "$(cat gated_10x_reference_target.txt)" = "$GATED_REFERENCE"
test -s "$GATED_REFERENCE"
test ! -L "$GATED_REFERENCE"
echo "Using genuine full GATED feature reference: $GATED_REFERENCE"

while IFS= read -r target; do
    snakemake -s workflow/Snakefile --configfile config/config.yaml -j1 \
        --printshellcmds --rerun-incomplete --latency-wait 120 --nolock "$target"
    test -s "$target"
done < gated_10x_subsample_targets.txt

python "$OLD/collect_metrics_from_targets.py" gated_10x_subsample_targets.txt
test ! -s results/gated_10x_subsample_targets_missing.txt
python collect_10x_gcn_gat_gated_comparison.py
