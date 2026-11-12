# PBMC GATED architecture comparison and cell subsampling

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

How does integration quality change across matched architectures and paired-cell subset sizes?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

GATED-GLUE.

Full reference + sizes 250/2000/8000 × subset seeds 0–2; model seed 0; gate_init=.95, lam_keep=0.

The canonical registry has **10 rows**. Reused rows and overlapping analysis views are not new independent fits.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [implementations/gated/evaluation/workflow/scripts/run_GLUE.py](../../../implementations/gated/evaluation/workflow/scripts/run_GLUE.py) |
| Configuration / manifest | [experiments/pbmc/gated_comparison/config.json](config.json)<br>[experiments/pbmc/gated_comparison/manifest.csv](manifest.csv) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py)<br>[evaluation/workflow/scripts/feature_consistency.py](../../../evaluation/workflow/scripts/feature_consistency.py)<br>[evaluation/workflow/scripts/combine_metrics.py](../../../evaluation/workflow/scripts/combine_metrics.py) |
| Plotting / reporting | [evaluation/collect_10x_gcn_gat_gated_comparison.py](../../../evaluation/collect_10x_gcn_gat_gated_comparison.py)<br>[evaluation/generate_gcn_gat_gated_metric_comparisons.py](../../../evaluation/generate_gcn_gat_gated_metric_comparisons.py)<br>[evaluation/compare_10x_gcn_vs_gat.py](../../../evaluation/compare_10x_gcn_vs_gat.py)<br>[evaluation/analyze_10x_gcn_vs_gat_statistics.py](../../../evaluation/analyze_10x_gcn_vs_gat_statistics.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_gated_comparison --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

## Artifacts and metrics

<output_root>/pbmc_gated_comparison/runs/<task_id> and metrics/<task_id>; historical /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/results_gated/raw/10x-Multiome-Pbmc10k/

Eight cell-integration metrics below, plus feature consistency only where the preserved configuration specifies a valid full-feature reference.

Integration keys: `mean_average_precision, normalized_mutual_info, avg_silhouette_width, graph_connectivity, seurat_alignment_score, avg_silhouette_width_batch, neighbor_conservation, foscttm`. Definitions remain in [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py).

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: 9 subsets evaluated + full reference. No new runtime reproduction.

Evaluation references task 0 of its own architecture. Three-way comparison uses only the nine common subset identities, not all 48 GCN/GAT subsets.

Historical GCN/GAT wrappers reference factored workflow directories and cluster paths; the clean launcher selects an explicit runner. Different prepared-input prefixes are recorded for GAT versus GCN/GATED; byte-equivalence of those input files was not assessed here.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
