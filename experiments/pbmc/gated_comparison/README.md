# PBMC GATED architecture comparison and cell subsampling

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/pbmc/gated_comparison`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `evaluation/workflow/scripts/run_GLUE.py in pinned gated implementation`

Evaluation: `evaluation/workflow/scripts/{cell_integration,feature_consistency,combine_metrics}.py`


The clean workflow requires the already-prepared RNA/ATAC, graph and 50D unirep files. It does not substitute a different preprocessing pipeline.

Status: 9 subsets evaluated + full reference
