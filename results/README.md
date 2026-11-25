# SHARE-seq GATED-GLUE — Evaluation PDFs

Supplementary figures and tables for 192 runs (16 embedding dimensions × 4 gate initializations × 3 seeds).

- [gate_distributions_complete.pdf](./gate_distributions_complete.pdf) — Learned-gate distributions across all 16 dimensions, shown by seed and seed mean, with all four initializations.
- [gate_suppression_complete.pdf](./gate_suppression_complete.pdf) — Gate-threshold suppression fractions, mean learned gates, and mean absolute changes across dimensions.
- [gate_reproducibility_complete.pdf](./gate_reproducibility_complete.pdf) — Spearman correlations and mean absolute gate differences across seeds and initializations.
- [gate_jaccard_pairwise_complete.pdf](./gate_jaccard_pairwise_complete.pdf) — Individual seed-pair and mean Jaccard overlaps, separated by initialization, for threshold and bottom-5% selections.
- [gate_bottomk_consensus_by_init.pdf](./gate_bottomk_consensus_by_init.pdf) — Bottom-1%, 5%, 10%, and 20% consensus across three seeds, reported separately for each initialization.
- [integration_metrics_all_runs.pdf](./integration_metrics_all_runs.pdf) — Eight integration-metric plots and the complete per-run tables for all 192 configurations.
- [consensus_strength.pdf](./consensus_strength.pdf) — Absolute-threshold consensus across all 12 runs and within each initialization; includes all-run and 75%-agreement views.
