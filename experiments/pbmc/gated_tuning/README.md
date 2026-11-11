# PBMC bounded GATED tuning, Stage A

Question: How do initial gate values and keep penalties affect integration?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_gated_tuning --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 15 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **15 Stage A configurations: 14 trained + one reused baseline; metrics not run; Stage B not designed**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: None identified in command construction; compute-node validation still required.

Evaluation blocker/limit: Stage A uses the original prepared RNA and ATAC as evaluation inputs, as specified in its batch script. Feature consistency is deferred until matched references exist. Stage B requires selected finalists.

## Implementation and provenance

* Training: `evaluation/run_gated_tuning_stageA.sbatch -> workflow/scripts/run_GLUE.py`
* Evaluation/analysis: `evaluation/run_gated_tuning_stageA_metrics.sbatch; select_gated_tuning_stageA.py`
* Owner: `gated`, preservation `GATED_SHARE_GATE_STABILITY` at `becf8f758f6d6869511e5d18732ce1f055a3cf03`.
* Historical submission files: `evaluation/run_gated_tuning_stage{A,A_metrics,B,B_metrics}.sbatch`
* Immutable source configuration: `evaluation/gated_tuning_stageA_configs.tsv`

Stage A gates .50,.75,.90,.95,.99 crossed with keep penalties 0,1e-5,1e-4; size2000/subset0/model0. The clean plan reads the historical .95/0 reference as a reused run. Stage B up to three finalists x subset seeds0–2 is planned only.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
