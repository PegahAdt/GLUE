# PBMC GAT one-factor tuning

Question: Which learning rate, loss weight or attention slope improves the matched comparison?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_gat_tuning --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 100 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **v2: 97/100 requested targets; three missing; v1 no requested outputs**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: None identified in command construction; compute-node validation still required.

Evaluation blocker/limit: Historical rule derives default-parameter full feature references; five extra full models exist. Review the exact historical reference mapping before selecting a clean metric policy. No silent replacement is made.

## Implementation and provenance

* Training: `GAT_GLUE:evaluation/workflow/scripts/run_GLUE.py`
* Evaluation/analysis: `historical Snakemake metric/reference rules; review reference selection before new evaluation`
* Owner: `orchestration`, preservation `GLUE_EXPERIMENT_ORCHESTRATION` at `88fee7ca07dfa25332d029d136887b651e57d313`.
* Historical submission files: `historical/gat_tuning/{submit.sh,run_one_config.sbatch}`
* Immutable source configuration: `evaluation/gat_tuning_10x/screen_v2/configs.tsv`, `evaluation/gat_tuning_10x/screen_v{1,2}/manifest.tsv`, `evaluation/gat_tuning_10x/screen_v{1,2}/configs/*/targets.txt`

Canonical design is v2. The old workers and wrappers are retained once under historical/gat_tuning. Use common/restore_workflow.py for byte-exact snapshots; restored launchers retain their historical blockers. New array mapping is config-major: full reference, then 3 sizes x 3 subset seeds, 100 rows total; historical mapping was 10 configuration jobs with 10 targets each.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.

The v1 parameter files match v2 byte for byte. v1 keeps distinct target paths and remains restorable from the preservation parent.
