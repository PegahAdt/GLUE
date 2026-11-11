# PBMC gcn graph subsampling

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/pbmc/gcn_graph_subsampling`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `evaluation/pbmc_graph_subsampling_gcn/scripts/train.py`

Evaluation: `evaluation/pbmc_graph_subsampling_gcn/scripts/evaluate.py`

Five conditions original and retain .75,.50,.25,.10 x model seeds0–2. Original GraphEncoder/GraphConv with audited constructors; no gates/attention. Requires successful frozen smoke and graph-validation records.

Status: 14/15 trained; task7 pending; evaluation waits
