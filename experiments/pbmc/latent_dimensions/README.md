# PBMC latent dimension comparison

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/pbmc/latent_dimensions`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `evaluation/dimension_sweep/run_dimension_train_array.sbatch`

Evaluation: `evaluation/dimension_sweep/run_{stageA,8000}_metrics.sbatch`

Dimensions16,32,50,64,100, subset/model seed0. Original arrays 0–11 for 2000 and separately 8000. Clean manifest concatenates 12+12+6 reused rows. GCN in this study deliberately uses the GAT branch with graph_encoder=gcn. It is not the separately audited original-GCN graph control. No non-50D feature-consistency metric is added.

Status: 30 configurations in metric tables; 24 fresh + six reused 50D; feature consistency deferred for non-50D
