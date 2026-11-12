# PBMC gate initialization sensitivity

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Does initial gate probability change integration or learned-edge distributions?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

GATED-GLUE.

Gate .50/.70/.90/.95/.99 × sizes 250/2000/8000 × subset seeds 0–2; model seed 0, keep=0. 45 rows: 36 fresh + nine .95 baseline reuses.

The canonical registry has **45 rows**. Reused rows and overlapping analysis views are not new independent fits.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/gate_init_sensitivity/run_training.sbatch](../../../evaluation/gate_init_sensitivity/run_training.sbatch)<br>[implementations/gated/evaluation/workflow/scripts/run_GLUE.py](../../../implementations/gated/evaluation/workflow/scripts/run_GLUE.py) |
| Configuration / manifest | [experiments/pbmc/gate_initialization/config.json](config.json)<br>[experiments/pbmc/gate_initialization/manifest.csv](manifest.csv) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/gate_init_sensitivity_metrics/evaluate_missing_metrics.py](../../../evaluation/gate_init_sensitivity_metrics/evaluate_missing_metrics.py)<br>[evaluation/gate_init_sensitivity_metrics/analyze_gate_init_metrics.py](../../../evaluation/gate_init_sensitivity_metrics/analyze_gate_init_metrics.py) |
| Plotting / reporting | [evaluation/gate_init_sensitivity_metrics/analyze_gate_init_metrics.py](../../../evaluation/gate_init_sensitivity_metrics/analyze_gate_init_metrics.py)<br>[evaluation/gate_init_sensitivity_report/analyze_gate_init_distributions.py](../../../evaluation/gate_init_sensitivity_report/analyze_gate_init_distributions.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_gate_initialization --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

## Artifacts and metrics

Historical new fits: /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/results_gate_init_sensitivity/gate_init:<g>/subsample_size:<n>-subsample_seed:<s>/model_seed:0; .95 reused references: GLUE_GATED/evaluation/results_gated/raw/10x-Multiome-Pbmc10k/... . Distribution/metric reports: /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/gate_init_sensitivity_{report,metrics}/. Clean future runs/metrics use <output_root>/pbmc_gate_initialization/.

Eight cell-integration metrics below, plus feature consistency only where the preserved configuration specifies a valid full-feature reference.

Integration keys: `mean_average_precision, normalized_mutual_info, avg_silhouette_width, graph_connectivity, seurat_alignment_score, avg_silhouette_width_batch, neighbor_conservation, foscttm`. Definitions remain in [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py).

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: 45 evaluated configurations; nine reused + 36 fresh. No new runtime reproduction.

Read exact preserved all_configurations.csv/training_tasks.csv. Historical source paths may contain carriage-return artifacts; no path normalization was performed. Uses historical GATED full feature reference.

This initialization grid includes .70; Stage-A tuning instead includes .75. Model seeds and subset seeds represent different sources of variation.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
