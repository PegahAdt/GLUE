# SHARE-seq GATED gate stability

Question: Are learned gates stable across initialization, model seeds and latent dimension?

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py share_gate_stability --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 0 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **A:109/144 finalized +35 pending; B:29/48 finalized +19 pending (one already trained); final analysis pending**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: Frozen source hashes and absolute output paths bind the 192-run design to the preserved cluster workspace. Relocation requires a separately validated provenance adapter; do not rerun prepare over the frozen manifest.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `evaluation/shareseq_gate_stability/experiment.py run A|B TASK`
* Evaluation/analysis: `evaluation/shareseq_gate_stability/analyze.py`
* Owner: `gated`, preservation `GATED_SHARE_GATE_STABILITY` at `becf8f758f6d6869511e5d18732ce1f055a3cf03`.
* Historical submission files: `evaluation/shareseq_gate_stability/submit.sh`, `evaluation/shareseq_gate_stability/slurm/array_{a,b}.sbatch`
* Immutable source configuration: `evaluation/shareseq_gate_stability/manifests/{all_runs,array_A,array_B,edges}.csv`, `evaluation/shareseq_gate_stability/preflight.json`

A:12 dimensions16–1024 x gates .25,.50,.75,.95 x seeds0–2=144. B:1536,2048,3072,4096 x same gates/seeds=48. Manifest row task_id is contiguous within A or B. Resources A4CPU/32G/3h30; B4CPU/48G/4h template, historically overridden to12h or18h. Retain exact original manifests/edge IDs/preflight. Analysis thresholds .25,.50,.75; all192 completion markers required. This catalog entry intentionally cannot submit into active paths.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
