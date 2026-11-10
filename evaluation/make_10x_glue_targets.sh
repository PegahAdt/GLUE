#!/bin/bash
set -eo pipefail

PRIOR="gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0"
HP="dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10"

DATASET="10x-Multiome-Pbmc10k"
SIZES=(250 500 1000 2000 4000 8000)
SUBSEEDS=(0 1 2 3 4 5 6 7)

: > glue_10x_targets.txt

for SIZE in "${SIZES[@]}"
do
  for SUBSEED in "${SUBSEEDS[@]}"
  do
    echo "results/raw/${DATASET}/subsample_size:${SIZE}-subsample_seed:${SUBSEED}/${PRIOR}/GLUE/${HP}/seed:0/metrics.yaml" >> glue_10x_targets.txt
  done
done

wc -l glue_10x_targets.txt
head glue_10x_targets.txt
tail glue_10x_targets.txt
