# PBMC bounded GATED tuning, Stage A

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

How do initial gate values and keep penalties affect integration?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

GATED-GLUE.

Gate .50/.75/.90/.95/.99 × keep 0/1e-5/1e-4; size 2000/subset seed 0/model seed 0; 15 rows, one historical .95/0 reuse.

The canonical registry has **15 rows**. Reused rows and overlapping analysis views are not new independent fits.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [implementations/gated/evaluation/workflow/scripts/run_GLUE.py](../../../implementations/gated/evaluation/workflow/scripts/run_GLUE.py)<br>[evaluation/run_gated_tuning_stageA.sbatch](../../../evaluation/run_gated_tuning_stageA.sbatch) |
| Configuration / manifest | [experiments/pbmc/gated_tuning/config.json](config.json)<br>[experiments/pbmc/gated_tuning/manifest.csv](manifest.csv) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/run_gated_tuning_stageA_metrics.sbatch](../../../evaluation/run_gated_tuning_stageA_metrics.sbatch)<br>[evaluation/collect_gated_tuning_stageA.py](../../../evaluation/collect_gated_tuning_stageA.py)<br>[evaluation/select_gated_tuning_stageA.py](../../../evaluation/select_gated_tuning_stageA.py) |
| Plotting / reporting | [evaluation/collect_gated_tuning_stageA.py](../../../evaluation/collect_gated_tuning_stageA.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_gated_tuning --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

## Artifacts and metrics

<output_root>/pbmc_gated_tuning/{runs,metrics}/<task_id>; historical /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/results_gated_tuning/stageA/<tag>/

Eight cell-integration metrics below. Gate extraction and feature-consistency claims are separate; matched SHARE evaluation does not calculate feature consistency.

Integration keys: `mean_average_precision, normalized_mutual_info, avg_silhouette_width, graph_connectivity, seurat_alignment_score, avg_silhouette_width_batch, neighbor_conservation, foscttm`. Definitions remain in [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py).

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: 15 Stage A configurations: 14 trained + one reused baseline; metrics not run; Stage B not designed. No new runtime reproduction.

Prepared RNA/ATAC are used directly for the historical Stage-A integration metric; feature consistency deferred. Stage-B finalist table depends on selector output.



Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
