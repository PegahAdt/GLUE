# PBMC GAT one-factor tuning

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Which learning rate, loss weight or attention slope improves the matched comparison?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

Raw-prior GAT-GLUE.

10 one-factor configurations × (one full + 3 sizes 250/2000/8000 × subset seeds 0–2) = 100 targets; model seed 0.

The canonical registry has **100 rows**. Reused rows and overlapping analysis views are not new independent fits.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [implementations/gat/evaluation/workflow/scripts/run_GLUE.py](../../../implementations/gat/evaluation/workflow/scripts/run_GLUE.py)<br>[historical/gat_tuning/run_one_config.sbatch](../../../historical/gat_tuning/run_one_config.sbatch) |
| Configuration / manifest | [experiments/pbmc/gat_tuning/config.json](config.json)<br>[experiments/pbmc/gat_tuning/manifest.csv](manifest.csv) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py)<br>[evaluation/workflow/scripts/feature_consistency.py](../../../evaluation/workflow/scripts/feature_consistency.py)<br>[evaluation/workflow/scripts/combine_metrics.py](../../../evaluation/workflow/scripts/combine_metrics.py) |
| Plotting / reporting | [evaluation/generate_gat_tuning_metrics_tex.py](../../../evaluation/generate_gat_tuning_metrics_tex.py)<br>[evaluation/generate_best_gat_vs_gcn_metrics_tex.py](../../../evaluation/generate_best_gat_vs_gcn_metrics_tex.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_gat_tuning --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**evaluation_blocker:** Historical rule derives default-parameter full feature references; five extra full models exist. Review the exact historical reference mapping before selecting a clean metric policy. No silent replacement is made.

## Artifacts and metrics

<output_root>/pbmc_gat_tuning/{runs,metrics}/<task_id>; historical B/evaluation/results_gat_tuning/screen_v2/<config>/raw/…

Eight cell-integration metrics below, plus feature consistency only where the preserved configuration specifies a valid full-feature reference.

Integration keys: `mean_average_precision, normalized_mutual_info, avg_silhouette_width, graph_connectivity, seurat_alignment_score, avg_silhouette_width_batch, neighbor_conservation, foscttm`. Definitions remain in [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py).

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: v2: 97/100 requested targets; three missing; v1 no requested outputs. No new runtime reproduction.

Defaults LR .002, lam_graph .02, lam_align .05, slope .2; varied LR .001/.0005, graph .01/.05, align .03/.08/.10, slope .05/.10/.40. Feature metric requires an explicit full-reference mapping.

v2 is authoritative; v1 is provenance. Catalog reports 97/100 historical targets, not verified completion during this audit.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
