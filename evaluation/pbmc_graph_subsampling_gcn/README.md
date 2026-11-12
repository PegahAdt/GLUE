# Original GLUE GCN guidance graph subsampling: PBMC

Research question: how does removal of biological guidance relations affect original GLUE integration? Five fixed guidance graphs (100%, 75%, 50%, 25%, 10%) × model seeds 0, 1, 2 give 15 runs; graph_seed=0. No randomized condition is included.

## Original architecture and matched settings

Training imports only `/project/6001426/paa40/GlUE_Exp/GLUE/scglue`, and executes that repository's unchanged `evaluation/workflow/scripts/run_GLUE.py`. Actual model instances must be the original `SCGLUEModel` with `sc.GraphEncoder` and `nn.GraphConv`, original graph decoder and NB likelihoods. Import paths, class identities, parameter names and checkpoint reloads are checked. Source hashes freeze the original implementation before training.

Shared settings match the completed GATED PBMC experiment: latent_dim=50, alt_dim=100, hidden depth=2, hidden dim=256, dropout=.2, lam_graph=.02, lam_align=.05, lr=.002, neg_samples=10, val_split=.1, data_batch_size=128, balance_res=1, balance_cutoff=.5, balance_power=4, convergence required. Original RNA HVG/PCA and ATAC all-peak LSI preprocessing, pretraining, balancing weights and fine-tuning remain unchanged. Full runs use the original automatic training schedule.

GCN has no gate initialization, gate parameters, gate regularization or attention. The original runner receives none of those arguments. Its constructor and losses are not replaced by GATED with gates fixed to one. An audit factory delegates to the original constructor and verifies its returned object before training. Only the smoke test bounds the original fit method to 50 pretraining epochs and two fine-tuning epochs; full training uses the original fit method without an epoch override. The original balancing-weight estimator is followed by a finite/nonnegative/nonempty weight check before fine-tuning, with no change to the estimator or alignment loss. An initial two-epoch pretraining smoke failed because the unchanged .5 cluster-matching cutoff produced nonfinite balancing weights; failed validation outputs are retained and full training was not submitted from them.

All baselines are fresh. A historical full-data seed-0 checkpoint and earlier reproduction checkpoints were inspected; historical source/preprocessing provenance is not frozen sufficiently for exact reuse, and some earlier runs rebuilt a different graph or used different preprocessing. No checkpoint is reused for the new experiment's baseline; existing artifacts are preserved.

## Exact graph subsets

`scripts/prepare.py` calls the existing `evaluation/workflow/scripts/graph_perturbation.py:subsample_reciprocal_pairs`. One seeded permutation supplies nested prefixes of sorted biological reciprocal pairs, retaining floor(f × 13493) pairs: 13493, 10119, 6746, 3373, 1349. All 15205 nodes/self-loops, retained edge attributes (including sign and weight), and reciprocal directions are preserved. These prepared graphs are shared by all three model seeds; the 100% graph is the unchanged original topology.

Metadata is checked against every corresponding completed GATED run. Complete prepared edge identities are also checked against the actual GATED seed-0 model in each condition. `graph_conditions.csv`, `validation/graph_verification.json`, graph SHA256 hashes and `validation/frozen_inputs.json` preserve that evidence. The GATED outputs remain untouched.

## Resources and validation

GPU array: one H100, 8 CPUs, 16 GiB, six hours per task, `0-14%3`. Original successful PBMC GCN job 52185979 used 8 CPUs/H100, completed with exit 0 in 41m35s, and had 8207364 KiB (7.83 GiB) batch MaxRSS. 16 GiB provides about twice that peak; six hours allows condition/seed variation. Accounting is recorded in `resource_usage.csv`. The 256-cell smoke can use the GPU launcher (45 minutes) or `smoke_cpu.sbatch` (8 CPUs, 16 GiB, one hour, no GPU). Both run on compute nodes and execute the same bounded original training stages. Training is refused without Slurm.

Prepare and test from the PBMC worktree root:

```bash
bash evaluation/pbmc_graph_subsampling_gcn/run.sh prepare
bash evaluation/pbmc_graph_subsampling_gcn/run.sh test
sbatch evaluation/pbmc_graph_subsampling_gcn/smoke.sbatch
```

If GPU availability delays validation, use `sbatch evaluation/pbmc_graph_subsampling_gcn/smoke_cpu.sbatch` instead. Use one smoke validation job at a time; both write the experiment's smoke-success record. The full experiment always uses the H100 GPU array.

The compute-node smoke runs both original training stages, reloads the final checkpoint, validates three saved embeddings, runs the existing PBMC metrics without gate diagnostics, and generates marked smoke reports. Only after all checks pass does it write `validation/smoke_success.json`.

After smoke succeeds, submit the 15-task array and its dependent CPU evaluation:

```bash
bash evaluation/pbmc_graph_subsampling_gcn/run.sh submit
```

If the smoke is queued, a small dispatcher may be submitted with `sbatch --dependency=afterok:SMOKE_JOB_ID --kill-on-invalid-dep=yes evaluation/pbmc_graph_subsampling_gcn/submit_validated.sbatch`. This dispatcher submits the training array only after successful smoke validation; it does not reserve training GPUs while validation is pending. `validation/smoke_submission.json` records smoke/dispatcher IDs; `submission.json` records actual training/evaluation IDs once submitted. Submission is idempotent and never duplicates an already recorded array.

## Evaluation and outputs

`scripts/evaluate.py` reuses the existing PBMC metric functions with `include_gates=False`. It copies the exact completed GATED evaluation settings, verifies original architecture and embeddings, and uses the exact same saved PCA/LSI references. Source barcode correspondence is verified, and embeddings are joined by identifier. Cell-type labels are WNN-derived references; modality labels are not biological annotations. Independent donor/batch metrics and canonical R kBET remain unsupported; the separately named fixed-k Pearson modality diagnostic follows the same shared definition.

The completed evaluation produces these files under `reports/full/`:

- `per_run_metrics.csv`, `summary_metrics.csv`, `baseline_comparison.csv`, `graph_statistics.csv`.
- `metric_availability.csv`, `condition_rankings.csv`, provenance and validation JSON files.
- `REPORT.md`, `REPORT.pdf`, `methodology.md`, `README.md`.
- `figures/*.png` (350 dpi) and `figures/*.pdf` (vector): retention trends, all-condition comparisons, seed variability, biological conservation versus modality mixing, metric correlations.

No gate metrics or gate-statistics table is generated. Means and sample SD use ddof=1 over model seeds; exact-cell retrieval and biological reference concordance are distinct. Only one dataset/graph seed and three model seeds are available, so conclusions and trends are descriptive, without claims of statistical significance. Full reporting requires all 15 completed runs. Smoke reports under `smoke/job_<ID>/evaluation/` are validation artifacts only.

Experiment layout:

```text
manifest.csv                 # 15 validated configurations
configurations/task_*.json   # per-run frozen training settings
graphs/<condition>.graphml.gz
validation/                 # source, graph, architecture and smoke evidence
logs/                       # Slurm stdout/stderr
smoke/job_<ID>/              # bounded training and gate-free evaluation
results/10x-Multiome-Pbmc10k/<condition>/graph_seed:0/model_seed:<seed>/
  pretrain/final.dill
  fine-tune/final.dill
  final.dill
  rna_latent.csv
  atac_latent.csv
  feature_latent.csv
  manifest.csv
  run_info.yaml
  architecture_verification.json
  completion.json
reports/full/               # generated only after all full runs complete
```

Progress and manual evaluation:

```bash
cat evaluation/pbmc_graph_subsampling_gcn/submission.json
squeue -u paa40
sacct -j TRAINING_JOB_ID --format=JobID,State,ExitCode,Elapsed,MaxRSS
tail -n 30 evaluation/pbmc_graph_subsampling_gcn/logs/train_TRAINING_JOB_ID_TASK_ID.out
sbatch --dependency=afterok:TRAINING_JOB_ID evaluation/pbmc_graph_subsampling_gcn/evaluate.sbatch
```

The submit command already schedules dependent evaluation. Full metric checkpoints are reused only under the same input/code/configuration fingerprint. Changed inputs or code require a fresh report output directory via `PBMC_GCN_EVAL_OUTPUT=/path/inside/this/experiment/reports/new sbatch --export=ALL evaluation/pbmc_graph_subsampling_gcn/evaluate.sbatch`. Existing training directories are refused rather than overwritten.
