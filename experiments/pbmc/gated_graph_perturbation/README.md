# PBMC gated graph perturbation

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/pbmc/gated_graph_perturbation`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `evaluation/pbmc_graph_perturbation/run_array.sbatch`

Evaluation: `evaluation/pbmc_graph_perturbation/scripts/evaluate.py`

Six conditions original,retain75/50/25/10,randomized x model seeds0–2. Graph seed0; 13493 reciprocal biological relations. Degree-preserving randomization10 accepted swaps per original relation, 134930 swaps;22 original relations remain. Full evaluator uses WNN reference annotations, not independent ground truth; canonical R kBET and independent donor batch measures unavailable.

Status: 18 trained and evaluated
