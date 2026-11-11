# PBMC bounded GATED tuning, Stage A

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/pbmc/gated_tuning`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `evaluation/run_gated_tuning_stageA.sbatch -> workflow/scripts/run_GLUE.py`

Evaluation: `evaluation/run_gated_tuning_stageA_metrics.sbatch; select_gated_tuning_stageA.py`

Stage A gates .50,.75,.90,.95,.99 crossed with keep penalties 0,1e-5,1e-4; size2000/subset0/model0. The clean fresh-replication plan trains all 15; historical .95/0 reuse remains documented. Stage B up to three finalists x subset seeds0–2 is planned only.

Status: 15 Stage A configurations: 14 trained + one reused baseline; metrics not run; Stage B not designed
