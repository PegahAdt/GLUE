# Randomized original GCN control: submission and verification

Three new randomized GCN runs are submitted; full training and combined evaluation are pending. The complete GCN design is 18 runs, six graph conditions and three model seeds per condition. No full-training/evaluation success is claimed.

| Job | ID | Verified status |
| --- | --- | --- |
| Existing 15-task training array | 64840335 | Unchanged, pending; indices 0–14%3 |
| Existing dependent evaluation | 64840336 | Unchanged, pending on 64840335 |
| Randomized CPU compute-node smoke | 64844073 | COMPLETED, exit 0:0; 6m36s on fc30554; MaxRSS 1,980,192 KiB |
| New randomized GPU training array | 64848480 | Pending; indices 0–2%3; model seeds 0,1,2 |
| New combined CPU evaluation | 64848481 | Pending; afterok:64840335:64848480 |

Slurm confirms both array-wide evaluation dependencies as unfulfilled. Evaluation cannot run unless both complete successfully. Submission uses `--kill-on-invalid-dep=yes`. GPU training resources match the existing array exactly: one H100, eight CPUs, 16 GiB and six hours. Evaluation uses eight CPUs, 48 GiB and six hours.

## Exact graph evidence

`validation/graph_verification.json` compares all three actual completed GATED randomized checkpoint endpoint identities and full deterministic reconstructed edge attributes. Original prior/code SHA256 and saved seed/swap parameters match the completed GATED evaluation. The original completed evaluator source was restored by reversing only its subsequently added gate-diagnostics switch, yielding the exact recorded SHA256; it is archived as `validation/completed_gated_evaluate.py`. No metric definition changed.

- 15,205 nodes and unchanged self-loops; 13,493 reciprocal biological relations; 42,191 directed edges.
- Graph seed 0; multiplier 10; 134,930 accepted swaps in 135,120 attempts.
- 22 original relations remain: 0.1630475061% overlap.
- Exact nodes/attributes, self-loops/attributes, per-node non-loop in/out-degree, bipartite and reciprocal structure, uniform weight=1/sign=1 semantics and complete attribute multisets are preserved.
- Edge identity plus complete attribute digest: `ce91deb2bd468d008104383a45437e933fb34e26c43b7aec61680de58fef3b15` for the new graph and every GATED reconstruction.
- Checkpoints retain endpoints; carried provenance attributes such as `dist`/`id` are verified through exact hash-verified deterministic reconstruction. Rewired `dist` is not a new biological distance.

## Architecture, configuration and smoke

Original-repository SCGLUEModel constructs sc.GraphEncoder/nn.GraphConv and the original graph decoder/NB modality likelihoods. Original source hashes, construction identities and loaded checkpoint architecture are audited; there are no gates, attention or GATED regularizers. Full-run preprocessing, raw input paths, original automatic schedule and all compatible non-graph parameters match the existing 15 GCN runs. The training wrapper differs only in experiment isolation, allowed task IDs and randomized graph provenance.

The compute-node smoke used 256 shared barcodes, 50 pretraining epochs and two fine-tuning epochs. It saved both stage checkpoints and the final checkpoint, reloaded the final checkpoint, validated finite RNA/ATAC 256×50 and feature 15,205×50 embeddings, computed gate-free metrics, and generated REPORT.md/REPORT.pdf with figures via pandoc/pdflatex. Its evaluation is explicitly a smoke validation, not a full-training result. Smoke artifacts: `smoke/job_64844073/`; evidence: `validation/smoke_success.json`. Automated verification: 31 tests passed before the extra source-audit test; all seven extension tests passed after that addition (32 unique passing tests).

## Files added

All extension files are under `evaluation/pbmc_graph_subsampling_gcn/randomized_control/`, except the added test:

- `scripts/common.py`, `prepare.py`, `freeze.py`: isolated design, exact graph/source equivalence and frozen-input guards.
- `scripts/train.py`: unchanged original-runner training logic adapted to the three separate tasks.
- `scripts/evaluate.py`, `gcn_report.py`: 18-run gate-free metrics, comparisons, plots, Markdown/PDF reports.
- `scripts/submit_pipeline.py`: smoke/test prerequisites, idempotent locked submission and both training dependencies.
- `manifest.csv` (three private array tasks), `combined_manifest.csv` (unchanged original prefix plus tasks 15–17), `configurations/task_0.json` through `task_2.json`.
- `graphs/randomized.graphml.gz`; `train_array.sbatch`, `smoke_cpu.sbatch`, `evaluate.sbatch`; README.md and this verification record.
- `validation/*`: graph/checkpoint/source proof, archived completed evaluator, tests/frozen inputs, smoke and final verification, Slurm resource snapshot.
- `submission.json`, `submission.lock`, new logs and smoke validation artifacts.
- `tests/test_pbmc_gcn_randomized.py`.

Original manifests, frozen inputs, wrapper scripts and launchers retain their exact saved hashes. Existing GATED checkpoints and evaluation inputs retain the completed-report hashes. Existing experiment outputs were not overwritten.

## Output directories

New full training:

`evaluation/pbmc_graph_subsampling_gcn/results/10x-Multiome-Pbmc10k/randomized/graph_seed:0/model_seed:<0|1|2>/`

New combined report:

`evaluation/pbmc_graph_subsampling_gcn/reports/combined_randomized_job_64848481/`

The new report will contain six-condition per-seed metrics and means/sample SD, GCN-versus-GATED per-seed/summary tables, architecture-specific original/randomized contrasts, FOSCTTM and matching-recall plots, biological conservation and graph-subsampling sensitivity figures, REPORT.md and REPORT.pdf. Exact completed GATED evaluation parameters and PCA/LSI reference hashes are reused. Gate-specific metrics remain exclusively in the existing GATED report. Existing `reports/full/` is preserved.

## Monitoring

Run from the PBMC worktree root:

```bash
cat evaluation/pbmc_graph_subsampling_gcn/randomized_control/submission.json
squeue -j 64840335,64840336,64848480,64848481 -o '%.24i %.24j %.10T %.120E %.30R'
sacct -j 64844073,64840335,64848480,64848481 --format=JobID,State,ExitCode,Elapsed,MaxRSS
sstat -j 64848480_0.batch --format=JobID,MaxRSS,AveCPU
tail -n 30 evaluation/pbmc_graph_subsampling_gcn/randomized_control/logs/train_64848480_0.out
tail -n 30 evaluation/pbmc_graph_subsampling_gcn/randomized_control/logs/evaluate_64848481.out
```

Do not resubmit the existing array. The extension submission command is idempotent and its submission.json records the actual jobs. Full training/evaluation status must be established from Slurm and completion records once the jobs finish.
