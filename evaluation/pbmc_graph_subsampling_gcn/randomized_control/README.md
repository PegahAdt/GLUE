# Original GCN randomized guidance control

This isolated extension adds randomized graph_seed=0/model_seed=0,1,2 to the original five-condition GCN experiment. The original 15-row manifest, launchers, jobs 64840335/64840336 and training/evaluation artifacts remain unchanged. `combined_manifest.csv` is a read-only combined design with old tasks 0–14 and randomized tasks 15–17; `manifest.csv` maps the separate new GPU array 0–2 to the three randomized model seeds.

The graph uses the existing `randomize_topology` implementation, original prior, seed 0 and swap multiplier 10. Original graph/code hashes match the completed GATED report. All complete edge attributes are compared against deterministic GATED reconstructions, and actual saved GATED checkpoint edge identities are checked for all three seeds. The graph has 15,205 nodes/self-loops, 13,493 reciprocal biological pairs and 42,191 directed edges; 134,930 accepted swaps leave 22 original relations (0.1630475061%). Per-node non-loop in/out-degree, bipartite/reciprocal structure, signed and weighted semantics and complete attribute multisets are preserved. `dist`/`id` are carried provenance, not new biological distances. Checkpoints retain endpoints rather than provenance attributes; full attribute evidence uses the hash-verified deterministic reconstruction. See `validation/graph_verification.json`. The shared evaluator already had an optional gate-diagnostics switch for GCN support; reversing only that switch reproduces the completed GATED evaluator SHA256 exactly. `validation/completed_gated_evaluate.py` archives that exact completed source; metric definitions are unchanged. Existing GCN-compatible plotting source is separately frozen for the new figures.

Separate wrappers copy the original experiment's training and gate-free evaluation logic, audited against the unchanged original GLUE repository. Full training uses the same raw RNA/ATAC inputs, preprocessing, settings, pretraining/balancing/fine-tuning, automatic convergence schedule and resources: one H100, eight CPUs, 16 GiB, six hours, array 0–2%3. Full runs are freshly initialized and refuse existing output directories. Smoke uses 256 shared barcodes, original preprocessing, 50 pretraining epochs and two fine-tuning epochs; checkpoint reload, finite 50D RNA/ATAC/feature embeddings, gate-free metrics and Markdown/PDF reports must all pass.

New training output: `../results/10x-Multiome-Pbmc10k/randomized/graph_seed:0/model_seed:<0|1|2>/`.

Combined evaluation waits with `afterok:64840335:NEW_RANDOMIZED_ARRAY` and `--kill-on-invalid-dep=yes`. It validates all 18 completion records/checkpoints/embeddings and generates six-condition per-seed/mean/sample-SD metrics, GCN versus completed GATED per-seed and summary tables, original/randomized comparisons, biological conservation, matching recall/FOSCTTM and retention plots, `REPORT.md` and `REPORT.pdf`. It copies the exact completed GATED evaluation parameters and PCA/LSI references. Gate metrics remain exclusive to the existing GATED report. It writes a new job-specific directory `../reports/combined_randomized_job_<EVALUATION_JOB_ID>/`, preserving `../reports/full/` and all prior reports. Full training/evaluation remain pending until Slurm jobs finish successfully.

Commands from the PBMC worktree root:

```bash
source evaluation/pbmc_graph_subsampling_gcn/environment.sh
export CUDA_VISIBLE_DEVICES=""
"$GCN_ENV/bin/python" -B evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/prepare.py
# Run automated extension tests, freeze its new files, then:
sbatch evaluation/pbmc_graph_subsampling_gcn/randomized_control/smoke_cpu.sbatch
# Only after smoke success:
"$GCN_ENV/bin/python" -B evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/submit_pipeline.py
cat evaluation/pbmc_graph_subsampling_gcn/randomized_control/submission.json
squeue -u paa40
sacct -j NEW_RANDOMIZED_ARRAY,NEW_EVALUATION_JOB --format=JobID,State,ExitCode,Elapsed,MaxRSS
tail -n 30 evaluation/pbmc_graph_subsampling_gcn/randomized_control/logs/train_NEW_RANDOMIZED_ARRAY_0.out
```

`validation/frozen_inputs.json` records the extension's code/manifests/graph and completed GATED comparison inputs. `validation/tests.json`, smoke-success and graph-verification records are submission prerequisites. No original source/loss function is edited. Three model seeds and one graph realization are descriptive replicates, not evidence of statistical significance; WNN-derived reference annotations and missing independent donor/batch labels retain the limitations of the existing matched evaluation.
