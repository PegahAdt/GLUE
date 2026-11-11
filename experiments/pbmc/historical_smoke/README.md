# Historical PBMC smoke and size250 reproduction

Question: Establish original GLUE and GAT environment/training viability.

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_historical_smoke --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 0 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **Original 1000-cell smoke and baseline smoke/full/GAT smoke artifacts exist; size250 eight seeds evaluated**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: Historical setup/reproduction view; use the canonical architecture comparison for new replication.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `historical/original_glue_checkout/smoke_train_10x_glue.sh; smoke_train_10x_gat.sh`
* Evaluation/analysis: `Run_On_fir historical metric workflow`
* Owner: `orchestration`, preservation `GLUE_EXPERIMENT_ORCHESTRATION` at `88fee7ca07dfa25332d029d136887b651e57d313`.
* Historical submission files: `historical/original_glue_checkout/*.sh`, `GLUE_Reproduction:Run_On_fir/**/*.sh`
* Immutable source configuration: 

Unique independent environment recipes remain in historical/original_glue_checkout. Reproduction commit731f9ba stores eight curated metric files. Some historical scripts source missing Run_On_fir/activate_glue.sh. No files are deleted because of age.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
