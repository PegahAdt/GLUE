# PBMC gate initialization sensitivity

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/pbmc/gate_initialization`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `evaluation/gate_init_sensitivity/run_training.sbatch`

Evaluation: `orchestration:evaluation/gate_init_sensitivity_{metrics,report}/*.py`

Gates .50,.70,.90,.95,.99; sizes250,2000,8000 x subset seeds0–2; model seed0. This differs from tuning gates (.75 instead of .70 there). Historical 36 directory names carry carriage returns; originals are preserved. Fresh clean output paths contain no CR. Distribution/report scripts are retained at their frozen source paths; the shared evaluator computes integration metrics only.

Status: 45 evaluated configurations; nine reused + 36 fresh
