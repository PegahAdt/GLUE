# PBMC latent dimension comparison

Question: How does embedding dimension affect each architecture at 2000 and 8000 paired cells?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_dimensions --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 27 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **30 configurations in metric tables; 24 fresh + six reused 50D; feature consistency deferred for non-50D**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: None identified in command construction; compute-node validation still required.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `evaluation/dimension_sweep/run_dimension_train_array.sbatch`
* Evaluation/analysis: `evaluation/dimension_sweep/run_{stageA,8000}_metrics.sbatch`
* Owner: `gated`, preservation `GATED_SHARE_GATE_STABILITY` at `becf8f758f6d6869511e5d18732ce1f055a3cf03`.
* Historical submission files: `evaluation/dimension_sweep/run_dimension_train_array.sbatch`, `evaluation/dimension_sweep/run_stageA_metrics.sbatch`, `evaluation/dimension_sweep/run_8000_metrics.sbatch`
* Immutable source configuration: `evaluation/dimension_sweep/{stageA_tasks,stageA_8000_tasks,reused_runs}.csv`

Dimensions16,32,50,64,100, subset/model seed0. Original arrays 0–11 for 2000 and separately 8000. Clean manifest concatenates 12+12+6 reused rows. GCN in this study deliberately uses the GAT branch with graph_encoder=gcn. It is not the separately audited original-GCN graph control. No non-50D feature-consistency metric is added.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
