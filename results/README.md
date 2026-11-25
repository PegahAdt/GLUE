# GLUE — Evaluation Results

Supplementary PDF figures and numerical results from GLUE experiments.

## SHARE-seq GATED-GLUE — Dimensionality and Gate Stability

192 runs: 16 embedding dimensions × 4 gate initializations × 3 random seeds.

- [gate_distributions_complete.pdf](./gate_distributions_complete.pdf) — Learned-gate distributions for all dimensions, shown separately by seed and as seed means, with the four initializations distinguished by color.
- [gate_suppression_complete.pdf](./gate_suppression_complete.pdf) — Fractions of low-gated edges, mean gate values, and changes from initialization across dimensions.
- [gate_reproducibility_complete.pdf](./gate_reproducibility_complete.pdf) — Spearman correlations and mean absolute gate differences across seeds and gate initializations.
- [gate_jaccard_pairwise_complete.pdf](./gate_jaccard_pairwise_complete.pdf) — Seed-pair Jaccard overlap and pairwise means for low-gated edges, reported separately for each initialization.
- [gate_bottomk_consensus_by_init.pdf](./gate_bottomk_consensus_by_init.pdf) — Consensus across three seeds for the bottom 1%, 5%, 10%, and 20% of edges, separated by initialization.
- [integration_metrics_all_runs.pdf](./integration_metrics_all_runs.pdf) — Plots of all eight integration metrics and tables of individual values for all 192 runs.
- [consensus_strength.pdf](./consensus_strength.pdf) — Absolute-threshold gate consensus across all 12 runs and within each initialization.

## GCN-GLUE — Guidance-Graph Perturbations

- [gcn_graph_subsampling_randomization.pdf](./gcn_graph_subsampling_randomization.pdf) — Eight integration metrics for 100%, 75%, 50%, 25%, and 10% graph-relationship retention and a degree-preserving randomized graph, with individual seed values, means, standard deviations, and subsampling plots.
