# SHARE-seq matched cell subsampling

Question: Compare all architectures on identical 8000/16000/24000-cell subsets and subset seeds0–2.

## Canonical workflow

From the orchestration checkout, inspect without changing files or contacting Slurm:

```bash
python3 -B experiments/launch.py share_matched_cells --dry-run --workspace experiments/workspace.example.json
```

`config.json` holds fixed settings and explicit resources; `manifest.csv`, when present,
maps zero-based array indices directly to configurations. It contains 18 rows.
Use `--task N` to inspect an individual command. Seeds are distinct model and cell-subset fields;
the latter remains traceable through `source_row` and input-directory identity.
Use `--phase train` or `--phase evaluate` to select a phase. `all` uses `afterok` dependencies.
Only `--submit` contacts Slurm; an exclusive external submission record prevents a second dispatch.
Existing or partial output directories are never overwritten. Preparation, model fitting and metric
code are the preserved entrypoints, selected explicitly by architecture.

Status at audit/cleanup review: **18 trained; nine GAT evaluated; nine GCN evaluations absent**. Manifest status columns in historical designs are
provenance, not live scheduler state. The clean command path has lightweight validation only;
no expensive training or end-to-end GPU reproduction was run during cleanup.

Launch blocker: None identified in command construction; compute-node validation still required.

Evaluation blocker/limit: Metric entrypoints unchanged; no large-data recomputation during cleanup.

## Implementation and provenance

* Training: `evaluation/shareseq_ma2020/scripts/matched_train_one.sh`
* Evaluation/analysis: `unchanged cell_integration.py via shared planner; historical evaluate_one.py/matched_evaluate_one.py`
* Owner: `orchestration`, preservation `GLUE_EXPERIMENT_ORCHESTRATION` at `88fee7ca07dfa25332d029d136887b651e57d313`.
* Historical submission files: `evaluation/shareseq_ma2020/slurm/matched_train_array.sbatch`, `evaluation/shareseq_ma2020/slurm/matched_evaluate_array.sbatch`
* Immutable source configuration: `evaluation/shareseq_ma2020/manifests/matched_subsample_manifest.csv`, `evaluation/shareseq_ma2020/manifests/{hyperparameters.yaml,subsampling.yaml,cells_*.txt}`

SHARE has 32231 paired cells. Canonical preparation/materialization and RNA PCA / ATAC LSI entrypoints are unchanged. The evaluator reads the exact recorded 50D RNA and ATAC representations. It verifies their SHA256 hashes, observation order, and latent dimensions before computing metrics. Bind the cache files through your workspace configuration. Gate extraction and aggregate reports remain explicitly separate historical analysis entrypoints; the generic EVALUATED marker means integration metrics only. No feature consistency is invented. Full dimension list:16,32,50,64,100,128,200,256,384,512,768,1024. The original 26-row study includes 15 full GATED initialization/seed combinations and nine GATED subsamples; these are reused views, not additional submissions.

Configure the Python environment, architecture checkout paths, input-prefix bindings,
partitions and a fresh external output directory in a copy of `workspace.example.json`.
Prepared inputs and original output directories are read-only dependencies. This launcher
does not download data or rerun preprocessing implicitly. Follow the preserved preparation
scripts and source fingerprints in the root reproducibility guide before a fresh replication.
