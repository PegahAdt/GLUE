# Reproduce the PBMC evaluation

From `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC`:

```bash
bash evaluation/pbmc_graph_perturbation/evaluate.sbatch preflight
bash evaluation/pbmc_graph_perturbation/evaluate.sbatch test
bash evaluation/pbmc_graph_perturbation/evaluate.sbatch smoke
sbatch evaluation/pbmc_graph_perturbation/evaluate.sbatch
```

The launcher reuses `/project/6001426/paa40/GlUE_Exp/GLUE/conda` with no installations, no GPU and no training. `preflight` checks all 18 embedding/metadata inputs; `test` runs focused automated tests; `smoke` evaluates one deterministic 100-cell-per-assay subset and generates clearly labeled demonstration artifacts. Full evaluation runs all 18 saved embeddings and derives shared 50D unimodal references in the reporting directory if absent. Substantial computation is refused outside Slurm unless the explicit `--allow-login` override is given to the Python CLI.

Output directories:

- `reports/preflight/`: input validation and pairing evidence, no metrics.
- `reports/smoke/`: sampled validation tables/figures/report, not scientific results.
- `reports/full/`: full tables, figures, report, provenance, references and checkpoints.

The full report directory contains `per_run_metrics.csv`, `summary_metrics.csv`, `baseline_comparison.csv`, `gate_statistics.csv`, `graph_statistics.csv`, `metric_availability.csv`, `condition_rankings.csv`, `REPORT.md`, `REPORT.pdf`, `methodology.md`, this README, and `figures/*.png` (350 dpi) / `figures/*.pdf` (vector). `figure_inventory.csv` lists actual figures, and `pdf_status.txt` explains the PDF backend. Pandoc/LaTeX is preferred; if unavailable or failing, a paginated text PDF is created with Matplotlib and vector figures remain separate.

Check `status.json`, `logs/evaluate_<jobid>.out` and `.err`. A complete full evaluation has `status=complete` and `n_evaluated_runs=18`; `smoke_complete` is not full completion. Submission evidence is stored in `reports/submission.json` when submitted by the implementation session.

Rerun the same Slurm command to reuse input-validated checkpoints. The pipeline refuses reuse when inputs, source code or parameters change: select a fresh directory with `PBMC_EVAL_OUTPUT=/absolute/report/directory sbatch --export=ALL evaluation/pbmc_graph_perturbation/evaluate.sbatch`. Existing embeddings and model results are never modified. Use a separate directory for a new evaluation configuration; this preserves previous results for comparison.

Presentation-only regeneration:

```bash
bash evaluation/pbmc_graph_perturbation/evaluate.sbatch report
```

CLI details:

```bash
PYTHONPATH="$PWD" PYTHONNOUSERSITE=1 \
LD_LIBRARY_PATH=/project/6001426/paa40/GlUE_Exp/GLUE/conda/lib \
/project/6001426/paa40/GlUE_Exp/GLUE/conda/bin/python -B \
evaluation/pbmc_graph_perturbation/scripts/evaluate.py --help
```

All metric parameters, library versions, source hashes, run-input hashes and source correspondence evidence are persisted. Definitions and limitations are in `methodology.md`. Each unavailable metric has a reason; independent batch metrics and canonical R/scIB kBET are distinguished from valid modality metrics and the explicitly named fixed-k Pearson variant.
