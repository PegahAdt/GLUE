# PBMC gate initialization sensitivity

Question: Does initial gate probability change integration or learned-edge distributions?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_gate_initialization --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 45 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **45 evaluated configurations; nine reused + 36 fresh**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: None identified in command construction; compute-node validation still required.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `evaluation/gate_init_sensitivity/run_training.sbatch`
* Evaluation/analysis: `orchestration:evaluation/gate_init_sensitivity_{metrics,report}/*.py`
* Owner: `gated`, preservation `GATED_SHARE_GATE_STABILITY` at `becf8f758f6d6869511e5d18732ce1f055a3cf03`.
* Historical submission files: `evaluation/gate_init_sensitivity/run_training.sbatch`
* Immutable source configuration: `evaluation/gate_init_sensitivity/{all_configurations,training_tasks}.csv`

Gates .50,.70,.90,.95,.99; sizes250,2000,8000 x subset seeds0–2; model seed0. This differs from tuning gates (.75 instead of .70 there). Historical 36 directory names carry carriage returns; originals are preserved. Fresh clean output paths contain no CR. Distribution/report scripts are retained at their frozen source paths; the shared evaluator computes integration metrics only.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
