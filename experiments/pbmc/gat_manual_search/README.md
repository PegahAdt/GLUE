# Planned adaptive GAT search

Question: Can a five-candidate screen followed by four validation runs improve integration?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py pbmc_gat_manual --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 0 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **Planned only; output directory absent**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: Historical manual search uses an unmatched feature reference. Adaptive winner selection must not be precomputed or silently repaired during cleanup.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `evaluation/run_gat_manual_search.py`
* Evaluation/analysis: `same adaptive search script`
* Owner: `orchestration`, preservation `GLUE_EXPERIMENT_ORCHESTRATION` at `88fee7ca07dfa25332d029d136887b651e57d313`.
* Historical submission files: `evaluation/wait_and_launch_gat_manual_search.sh`, `evaluation/run_gat_manual_search_in_allocation.sh`
* Immutable source configuration: 

Candidates (graph,align,slope): (.04,.05,.10),(.05,.04,.10),(.05,.05,.10),(.05,.06,.10),(.06,.05,.10). Screen size2000/subset0, then winner at (2000,1),(2000,2),(250,0),(8000,0).

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
