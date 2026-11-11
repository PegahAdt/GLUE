# PBMC gcn graph subsampling

Question: How does guidance-graph structure affect integration under matched architecture and data?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_gcn_graph_subsampling --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 0 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **14/15 trained; task7 pending; evaluation waits**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: Frozen cluster pipeline retained byte-for-byte. Its absolute-path/source-hash guards must be preserved; a fresh portable freeze and validated smoke are required before dispatch from a relocated checkout.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `evaluation/pbmc_graph_subsampling_gcn/scripts/train.py`
* Evaluation/analysis: `evaluation/pbmc_graph_subsampling_gcn/scripts/evaluate.py`
* Owner: `pbmc`, preservation `GATED_PBMC_GRAPH_EXPERIMENTS` at `2ead2851a06b3aaec969e83c61eccb05b1d0c5dd`.
* Historical submission files: `evaluation/pbmc_graph_subsampling_gcn/train_array.sbatch`, `evaluation/pbmc_graph_subsampling_gcn/evaluate.sbatch`
* Immutable source configuration: `evaluation/pbmc_graph_subsampling_gcn/manifest.csv`, `evaluation/pbmc_graph_subsampling_gcn/validation/frozen_inputs.json`

Five conditions original and retain .75,.50,.25,.10 x model seeds0–2. Original GraphEncoder/GraphConv with audited constructors; no gates/attention. Requires successful frozen smoke and graph-validation records.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
