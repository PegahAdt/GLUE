# PBMC GCN architecture comparison and cell subsampling

Question: How does integration quality change across matched architectures and paired-cell subset sizes?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_gcn_comparison --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 49 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **48 subsets evaluated + full reference**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: None identified in command construction; compute-node validation still required.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `evaluation/workflow/scripts/run_GLUE.py in pinned gcn implementation`
* Evaluation/analysis: `evaluation/workflow/scripts/{cell_integration,feature_consistency,combine_metrics}.py`
* Owner: `orchestration`, preservation `GLUE_EXPERIMENT_ORCHESTRATION` at `88fee7ca07dfa25332d029d136887b651e57d313`.
* Historical submission files: `evaluation/run_10x_gcn_reference.sh`, `evaluation/run_10x_gcn_subsamples.sh`
* Immutable source configuration: `evaluation/gcn_h100_10x_subsample_targets.txt`, `evaluation/gcn_h100_10x_reference_target.txt`


The clean workflow requires the already-prepared RNA/ATAC, graph and 50D unirep files. It does not substitute a different preprocessing pipeline.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.

The full reference is clean task 0. Tasks 1 through 48 follow the preserved target list in its original order.
