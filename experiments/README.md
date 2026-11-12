# Research experiment catalog

[Research overview](../README.md) · [Thesis correspondence](../THESIS_EXPERIMENTS.md) · [Reproduction guide](../REPRODUCIBILITY.md)

Use directories and immutable manifests on this branch rather than switching experiment branches. Historical `owner` and `preservation_branch` fields in `catalog.json` retain provenance; the included code is mapped through `provenance/experiment_map.json`. Planning is not proof of executable portability or result completion.

| Catalog ID | Experiment | Status / limitation |
|---|---|---|
| pbmc_gcn_comparison | [PBMC GCN architecture comparison and cell subsampling](pbmc/gcn_comparison/README.md) | Historical audit: 48 subsets evaluated + full reference. No new runtime reproduction. |
| pbmc_gat_comparison | [PBMC GAT architecture comparison and cell subsampling](pbmc/gat_comparison/README.md) | Historical audit: 48 subsets evaluated + full reference; historical GAT Snakemake binding broken. No new runtime reproduction. |
| pbmc_gated_comparison | [PBMC GATED architecture comparison and cell subsampling](pbmc/gated_comparison/README.md) | Historical audit: 9 subsets evaluated + full reference. No new runtime reproduction. |
| pbmc_gat_tuning | [PBMC GAT one-factor tuning](pbmc/gat_tuning/README.md) | Historical audit: v2: 97/100 requested targets; three missing; v1 no requested outputs. No new runtime reproduction. |
| pbmc_gat_manual | [Planned adaptive GAT search](pbmc/gat_manual_search/README.md) | Adaptive plan/source retained; finalized execution and feature-reference policy unresolved. |
| pbmc_gated_tuning | [PBMC bounded GATED tuning, Stage A](pbmc/gated_tuning/README.md) | Historical audit: 15 Stage A configurations: 14 trained + one reused baseline; metrics not run; Stage B not designed. No new runtime reproduction. |
| pbmc_dimensions | [PBMC latent dimension comparison](pbmc/latent_dimensions/README.md) | 30 registered conditions: 24 non-50D and six reused 50D references. Registry correction complete; no fresh GPU reproduction. |
| pbmc_gate_initialization | [PBMC gate initialization sensitivity](pbmc/gate_initialization/README.md) | Historical audit: 45 evaluated configurations; nine reused + 36 fresh. No new runtime reproduction. |
| pbmc_gate_analysis | [PBMC learned edge analysis](pbmc/learned_edge_analysis/README.md) | Historical audit: Ten reused models analyzed; generated reports excluded. No new runtime reproduction. |
| share_primary | [SHARE-seq architecture comparison](shareseq/architecture_comparison/README.md) | Historical audit: 26 trained and evaluated. No new runtime reproduction. |
| share_matched_cells | [SHARE-seq matched cell subsampling](shareseq/matched_cell_subsampling/README.md) | Dated audit: 18 checkpoint paths; nine GAT metric files and no matching GCN metric files. Evaluation incomplete. |
| share_dimensions | [SHARE-seq full data dimensions](shareseq/full_data_dimensions/README.md) | Historical audit: 36 validated metric directories; three reused 50D. No new runtime reproduction. |
| share_gate_stability | [SHARE-seq GATED gate stability](shareseq/gate_stability/README.md) | 192 planned conditions; 139 retained checkpoint paths and matching Python-version/job provenance in the dated audits. Aggregate analysis incomplete; frozen portability blocked. |
| pbmc_gated_graph | [PBMC gated graph perturbation](pbmc/gated_graph_perturbation/README.md) | Historical audit: 18 trained and evaluated. No new runtime reproduction. |
| pbmc_gcn_graph_subsampling | [PBMC gcn graph subsampling](pbmc/gcn_graph_subsampling/README.md) | 15 registered conditions; 14 checkpoint paths in the dated audit. Frozen pipeline; no fresh reproduction. |
| pbmc_gcn_randomized | [PBMC gcn graph randomization](pbmc/gcn_graph_randomization/README.md) | Historical audit: 3/3 trained; combined18-run evaluation waits on retention task7. No new runtime reproduction. |
| pbmc_historical_smoke | [Historical PBMC smoke and size250 reproduction](pbmc/historical_smoke/README.md) | Historical audit: Original 1000-cell smoke and baseline smoke/full/GAT smoke artifacts exist; size250 eight seeds evaluated. No new runtime reproduction. |
| gat_normalized | [Normalized guidance-edge GAT variant](pbmc/normalized_gat/README.md) | Implementation and test source only; no verified thesis experiment manifest or results. |
| upstream_suites | [Inherited upstream experimental suites](common/upstream_suites/README.md) | Historical audit: Configured source; no verified local case-study model outputs. No new runtime reproduction. |

SHARE initialization/cell-size views overlap the primary manifest. Upstream case studies remain under their original directories and are not claimed as new thesis contributions. Stage-B finalist selection, normalized-GAT study design and dedicated SHARE edge-retention coverage remain plans/unverified. The 880 historical workflows remain factored into common templates and restoration metadata; they were not expanded.
