# Initial PBMC guidance-graph experiment

This experiment uses the `GATED_PBMC_GRAPH_EXPERIMENTS` branch in
`/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC`. It has 18 runs: six graph
conditions, each with model seeds 0, 1 and 2. The graph seed is explicitly 0
for every run, including the original condition. Graph replicates are held
fixed while model randomness varies.

`manifest.csv` is the run configuration. Its columns are `task_id`,
`condition`, `graph_perturbation`, `retain_fraction`, `swap_multiplier`,
`graph_seed`, `model_seed`, and `run_dir`. Empty fraction/multiplier cells
mean the parameter is inactive; those options are omitted from the command.
Task IDs must be contiguous, and the launcher validates every row against
this initial experiment before executing any task.

| Task IDs | Condition | Perturbation | Active parameter | Model seeds |
|---|---|---|---|---|
| 0, 1, 2 | original | none | — | 0, 1, 2 |
| 3, 4, 5 | retain_75 | subsample | fraction 0.75 | 0, 1, 2 |
| 6, 7, 8 | retain_50 | subsample | fraction 0.50 | 0, 1, 2 |
| 9, 10, 11 | retain_25 | subsample | fraction 0.25 | 0, 1, 2 |
| 12, 13, 14 | retain_10 | subsample | fraction 0.10 | 0, 1, 2 |
| 15, 16, 17 | randomized | randomize | swap multiplier 10.0 | 0, 1, 2 |

The shared hyperparameters match the GATED reference: `dim=50`,
`alt_dim=100`, `hidden_depth=2`, `hidden_dim=256`, `dropout=0.2`,
`lam_graph=0.02`, `lam_align=0.05`, `lr=0.002`, `neg_samples=10`,
`data_batch_size=128`, `graph_encoder=gated`, `gate_init=0.95`, and
`lam_keep=0.0`. Training requires convergence, as in the reference run.

The launcher reads the existing data directly from:

```text
/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/results_gcn_h100/raw/10x-Multiome-Pbmc10k/original/
├── rna.h5ad
├── atac.h5ad
└── gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/sub.graphml.gz
```

It reuses the reference conda environment at
`/project/6001426/paa40/GlUE_Exp/GLUE/conda`, activates it with micromamba,
and sets `PYTHONPATH` to this PBMC worktree. No input copies or new input
symlinks are created, and no old result directories are used.

Results are isolated under:

```text
evaluation/pbmc_graph_perturbation/
├── .gitignore
├── manifest.csv
├── resource_usage.csv
├── README.md
├── run_array.sbatch
├── logs/train_<array_job_id>_<task_id>.{out,err}
└── results/10x-Multiome-Pbmc10k/<condition>/graph_seed:0/model_seed:<seed>/
    ├── manifest.csv
    ├── run_GLUE.log
    ├── run_info.yaml
    ├── gate_diagnostics.yaml
    ├── rna_latent.csv
    ├── atac_latent.csv
    ├── feature_latent.csv
    ├── final.dill
    ├── pretrain/
    └── fine-tune/
```

Slurm requests one H100, 8 CPUs, 16G RAM, and 6 hours per array task.
The array is `0-17%3`, limiting concurrency to three tasks. The tracked
`logs/.gitkeep` ensures the Slurm log directory exists before submission.
Every successful task must produce both YAML files and all model/latent
outputs. Existing run directories are refused rather than overwritten;
failed runs therefore need an explicit decision before retrying.

The memory request is based on successful PBMC GATED runs from August 10,
2026, inspected with `sacct` on September 30, 2026. `resource_usage.csv`
records their actual batch-step MaxRSS values and elapsed times. Each job
and batch step completed with exit code `0:0`, and each result directory
contains nonempty model/latent outputs, `run_info.yaml`, and
`gate_diagnostics.yaml`. Failed earlier attempts were excluded.

| Job | Prior PBMC input | MaxRSS (KiB) | MaxRSS (GiB) | Elapsed |
|---|---|---:|---:|---|
| 54007911 | Full original data | 7,203,276 | 6.870 | 00:35:38 |
| 54007910_1 | 250 cells/modality, subsample seed 1 | 6,605,320 | 6.299 | 00:47:26 |
| 54007910_2 | 250 cells/modality, subsample seed 2 | 7,068,556 | 6.741 | 00:46:53 |
| 54007910_3 | 2,000 cells/modality, subsample seed 0 | 6,128,676 | 5.845 | 00:31:54 |
| 54007910_4 | 2,000 cells/modality, subsample seed 1 | 5,785,876 | 5.518 | 00:31:54 |
| 54007910_5 | 2,000 cells/modality, subsample seed 2 | 6,139,504 | 5.855 | 00:32:07 |
| 54007910_6 | 8,000 cells/modality, subsample seed 0 | 7,171,128 | 6.839 | 00:35:40 |
| 54007910_7 | 8,000 cells/modality, subsample seed 1 | 6,850,884 | 6.534 | 00:35:45 |
| 54007910_8 | 8,000 cells/modality, subsample seed 2 | 6,102,392 | 5.820 | 00:37:36 |

The full original run has the largest measured peak, about 6.87 GiB.
A 16G request provides roughly 2.33 times that observed peak, leaving room
for graph copies, model seed variation, and runtime variation. MaxRSS is host
memory usage; it does not measure GPU memory. The six-hour limit is the
initial experimental limit; previous graph perturbation training runtimes
have not yet been measured. Reproduce the accounting query with:

```bash
sacct -j 54007911,54007910 -S 2026-08-01 -E 2026-08-15 \
  --format=JobID,State,ExitCode,Start,End,Elapsed,MaxRSS,ReqMem -n -P
```

Inspect from the repository root without submitting or training:

```bash
cat evaluation/pbmc_graph_perturbation/manifest.csv
bash -n evaluation/pbmc_graph_perturbation/run_array.sbatch
DRY_RUN=1 bash evaluation/pbmc_graph_perturbation/run_array.sbatch
DRY_RUN=1 bash evaluation/pbmc_graph_perturbation/run_array.sbatch 15
```

Dry-run mode verifies the branch, existing inputs, and all 18 manifest rows,
then prints shell-escaped commands and log destinations. With no argument
(or `all`) it prints every command; a task ID prints only that command. It
does not activate the environment, create outputs, execute Python, or submit
jobs. `PBMC_GRAPH_MANIFEST=/path/to/manifest.csv` can select a frozen copy
of the same configuration; every row remains subject to the same validation.
Outside dry-run mode, the script requires a Slurm array task environment.

The runner records graph configuration/metadata in `run_info.yaml`, keeps
all graph nodes and self-loops, and refuses incomplete randomization before
training. Subsampling fractions use nested reciprocal-pair subsets for the
fixed graph seed. Randomization requests 134,930 successful swaps on the
13,493 original biological relations; residual original overlap is recorded
by the runner rather than assumed to be zero.
