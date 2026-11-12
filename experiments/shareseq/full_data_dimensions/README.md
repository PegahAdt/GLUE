# SHARE-seq full data dimensions

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Compare 12 full-data latent dimensions across GCN/GAT/GATED, model seed0.

## Dataset, architectures and conditions

Ma-2020 mouse-skin SHARE-seq, 32,231 paired RNA/ATAC cells in preserved ordering.

GCN/GAT/GATED.

36 rows: three architectures × dimensions 16/32/50/64/100/128/200/256/384/512/768/1024; model seed0, fixed full cells; three 50D references reused.

The canonical registry has **36 rows**. Reused rows and overlapping analysis views are not new independent fits.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/shareseq_ma2020/scripts/full_dimension_train_one.sh](../../../evaluation/shareseq_ma2020/scripts/full_dimension_train_one.sh) |
| Configuration / manifest | [experiments/shareseq/full_data_dimensions/config.json](config.json)<br>[experiments/shareseq/full_data_dimensions/manifest.csv](manifest.csv) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/shareseq_ma2020/scripts/full_dimension.py](../../../evaluation/shareseq_ma2020/scripts/full_dimension.py) |
| Plotting / reporting | [evaluation/shareseq_ma2020/scripts/full_dimension_report.py](../../../evaluation/shareseq_ma2020/scripts/full_dimension_report.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py share_dimensions --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

## Artifacts and metrics

<output_root>/share_dimensions/{runs,metrics}/<task_id>; historical B/evaluation/shareseq_ma2020/results/<run_id>; metrics/, analysis/, reports/ under the same historical experiment root.

Eight cell-integration metrics below. Gate extraction and feature-consistency claims are separate; matched SHARE evaluation does not calculate feature consistency.

Integration keys: `mean_average_precision, normalized_mutual_info, avg_silhouette_width, graph_connectivity, seurat_alignment_score, avg_silhouette_width_batch, neighbor_conservation, foscttm`. Definitions remain in [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py).

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: 36 validated metric directories; three reused 50D. No new runtime reproduction.

Prepared shared cells/graph, ordered cell manifests, pinned architecture sources, exact recorded 50D PCA/LSI in experiments/shareseq/unirep_references.json. Gate extraction is separate from integration evaluation.

Catalog notes incorrectly describe newly generated isolated 50D evaluation representations; launch.py actually reads and verifies the recorded representations. Historical matched_postprocess.py claims feature consistency in prose although matched_evaluate_one.py validates only eight integration metrics. Full-dimension submission used recorded inline sbatch commands rather than a reusable full-array batch file.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
