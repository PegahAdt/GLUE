# Normalized guidance-edge GAT variant

Question: How would normalized rather than raw prior weights affect GAT?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py gat_normalized --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 0 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **Implementation and unit tests only; no verified local experiment design or outputs**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: No experiment manifest or verified execution; do not invent a scientific configuration.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `GAT_NORM_GLUE:evaluation/workflow/scripts/run_GLUE.py`
* Evaluation/analysis: `no executed experiment evaluator`
* Owner: `orchestration`, preservation `GLUE_EXPERIMENT_ORCHESTRATION` at `88fee7ca07dfa25332d029d136887b651e57d313`.
* Historical submission files: 
* Immutable source configuration: 

Architecture commit5ac0b073a5f0a372a472605d8fc61a39def55b31; unit test tests/test_gat_normalized_weights.py. This is an architecture option, not completed experiment evidence.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
