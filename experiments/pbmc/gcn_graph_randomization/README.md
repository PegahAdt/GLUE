# PBMC gcn graph randomization

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/pbmc/gcn_graph_randomization`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/train.py`

Evaluation: `evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/evaluate.py`

Three randomized controls plus combined_manifest.csv18rows. Original evaluator snapshot under validation/completed_gated_evaluate.py is scientifically frozen reference code, not an unnecessary duplicate. Original combined dependency afterok:64840335:64848480; replacement evaluation currently afterok:3069635.

Status: 3/3 trained; combined18-run evaluation waits on retention task7
