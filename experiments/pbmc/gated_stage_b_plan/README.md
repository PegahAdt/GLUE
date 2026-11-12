# PBMC selected-finalist GATED Stage B (planned)

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Validate up to three Stage-A finalists across subset seeds.

## Dataset, architectures and conditions

PBMC RNA/ATAC, size2000 validation design in selector/source.

GATED-GLUE.

Proposed up to three finalists × subset seeds0–2; exact finalized rows not specified.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/run_gated_tuning_stageB.sbatch](../../../evaluation/run_gated_tuning_stageB.sbatch) |
| Configuration / manifest | [evaluation/gated_tuning_design.md](../../../evaluation/gated_tuning_design.md) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/run_gated_tuning_stageB_metrics.sbatch](../../../evaluation/run_gated_tuning_stageB_metrics.sbatch) |
| Plotting / reporting | [evaluation/select_gated_tuning_stageA.py](../../../evaluation/select_gated_tuning_stageA.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

No executable training command is supplied for this unresolved plan. Inspect the listed selector/source; do not invent or launch finalists.

## Artifacts and metrics

Historical GLUE_GATED/evaluation/results_gated_tuning/stageB/<tag>/

Eight cell-integration metrics below. Gate extraction and feature-consistency claims are separate; matched SHARE evaluation does not calculate feature consistency.

Integration keys: `mean_average_precision, normalized_mutual_info, avg_silhouette_width, graph_connectivity, seurat_alignment_score, avg_silhouette_width_batch, neighbor_conservation, foscttm`. Definitions remain in [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py).

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Plan only: finalized selector output and approved finalist conditions not established.

Stage-A metrics and select_gated_tuning_stageA.py must establish finalists; batch scripts require gated_tuning_stageB_configs.tsv.

This is an explicit planned descendant, not evidence of completed Stage-B models.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
