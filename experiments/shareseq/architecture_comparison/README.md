# SHARE-seq architecture comparison

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Compare full-data architectures, GATED subsampling and full-data gate initialization.

## Dataset, architectures and conditions

Ma-2020 mouse-skin SHARE-seq, 32,231 paired RNA/ATAC cells in preserved ordering.

GCN/GAT/GATED.

26 rows: three full primary architectures (GATED .95/model0 overlaps initialization), nine GATED cell subsets (8000/16000/24000 × subset seeds 0–2, model0), full GATED .50/.70/.90/.95/.99 × model seeds 0–2. Those views overlap and must not be summed as new runs.

The canonical registry has **26 rows**. Reused rows and overlapping analysis views are not new independent fits.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/shareseq_ma2020/scripts/train_one.sh](../../../evaluation/shareseq_ma2020/scripts/train_one.sh) |
| Configuration / manifest | [experiments/shareseq/architecture_comparison/config.json](config.json)<br>[experiments/shareseq/architecture_comparison/manifest.csv](manifest.csv) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/shareseq_ma2020/scripts/evaluate_one.py](../../../evaluation/shareseq_ma2020/scripts/evaluate_one.py) |
| Plotting / reporting | [evaluation/shareseq_ma2020/scripts/postprocess.py](../../../evaluation/shareseq_ma2020/scripts/postprocess.py)<br>[evaluation/shareseq_ma2020/scripts/build_current_results_report.py](../../../evaluation/shareseq_ma2020/scripts/build_current_results_report.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py share_primary --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

## Artifacts and metrics

<output_root>/share_primary/{runs,metrics}/<task_id>; historical B/evaluation/shareseq_ma2020/results/<run_id>; metrics/, analysis/, reports/ under the same historical experiment root.

Eight cell-integration metrics below. Gate extraction and feature-consistency claims are separate; matched SHARE evaluation does not calculate feature consistency.

Integration keys: `mean_average_precision, normalized_mutual_info, avg_silhouette_width, graph_connectivity, seurat_alignment_score, avg_silhouette_width_batch, neighbor_conservation, foscttm`. Definitions remain in [evaluation/workflow/scripts/cell_integration.py](../../../evaluation/workflow/scripts/cell_integration.py).

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: 26 trained and evaluated. No new runtime reproduction.

Prepared shared cells/graph, ordered cell manifests, pinned architecture sources, exact recorded 50D PCA/LSI in experiments/shareseq/unirep_references.json. Gate extraction is separate from integration evaluation.

Primary study also contains a distinct full-data GATED initialization sensitivity view and a GATED cell-size view. Those are scientific subdesigns, not separate independent task sets. SHARE graph is fixed at corrupt_rate=0; cell subsampling is not graph-edge subsampling.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
