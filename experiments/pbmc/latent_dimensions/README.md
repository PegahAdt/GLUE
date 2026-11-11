# PBMC latent dimension comparison

Question: How does embedding dimension affect each architecture at 2000 and 8000 paired cells?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_dimensions --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 30 rows.
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

Dimensions16,32,50,64,100, subset/model seed0. Original arrays 0–11 for 2000 and separately 8000. The clean manifest contains 12+12 non-50D configurations and six reused 50D references. Fresh GCN dimension jobs use the GAT branch with graph_encoder=gcn. This does not establish the exact source version of the historical references or identify them with the separately audited original-GCN graph control. No non-50D feature-consistency metric is added.

## Restored 8,000-cell references

Task IDs 27–29 reference the existing GCN, GAT and GATED 8,000-cell, 50D runs,
respectively, with subset/model seeds 0/0. IDs 0–26 are unchanged. The three
added rows have `reuse_source` set to the preserved comparison directories;
the training handler returns before model execution. With the existing
`reuse_metrics: true` setting, their saved 50D metric YAMLs are reused.
The 24 fresh-replication configurations remain unchanged. The dispatcher
still includes reuse rows in its array mapping; they do not fit new models.
No submission is needed to reconcile the existing results.

Additional acceptance source:
`/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep/available_8000_runs.csv`,
SHA256 `2aac1d31c9d0bdeaa20f03395c4f7a6919e726a027d881b3f7f614d5066b1790`.
The new `source_row` values identify zero-based data rows 2, 7 and 12
(physical CSV lines 4, 9 and 14). Input paths retain each run's recorded
prepared data and graph; graph checksums identify the original bytes.
Checkpoints, embeddings, evaluations and numerical results were not changed.

Historical run metadata records encoder mode and scientific settings but does
not pin an exact per-run Git commit/source hash. The `implementation` field
selects the current checkout used by the launcher; it does not retroactively
establish the source version used to train a reused model. In particular,
the reused GCN metadata has a GAT-compatible GCN CLI. No missing version was
inferred or invented.

Before this correction, the 27-row manifest at commit
`5229903907c940a4b2740d7615ce2bd6d8e1bafa` had SHA256
`2e0b0a5c1de456ac130e570cf57ea5282c6f47a6e2e415678cb9df42002d1293`.
Its original bytes were preserved separately before appending the references.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
