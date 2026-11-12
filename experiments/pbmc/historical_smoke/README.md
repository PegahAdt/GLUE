# Historical PBMC smoke and size250 reproduction

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Establish original GLUE and GAT environment/training viability.

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

Historical original GCN and GAT smoke/reproduction views.

Size250 wrappers specify subset seeds via target lists; eight-seed reproduction view is historical. Smoke scripts select limited datasets/iterations and must not be treated as a final scientific protocol.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [historical/original_glue_checkout/smoke_train_10x_glue.sh](../../../historical/original_glue_checkout/smoke_train_10x_glue.sh)<br>[evaluation/run_10x_seed0_size250.sh](../../../evaluation/run_10x_seed0_size250.sh)<br>[evaluation/run_10x_size250_allseeds.sh](../../../evaluation/run_10x_size250_allseeds.sh) |
| Configuration / manifest | [experiments/pbmc/historical_smoke/config.json](config.json) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/collect_metrics_from_targets.py](../../../evaluation/collect_metrics_from_targets.py) |
| Plotting / reporting | [evaluation/print_completed_latex_table.py](../../../evaluation/print_completed_latex_table.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_historical_smoke --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**launch_blocker:** Historical setup/reproduction view; use the canonical architecture comparison for new replication.

## Artifacts and metrics

Historical original checkout data/dataset/*-glue-ready.h5ad and smoke output paths; B/evaluation/results*/raw/…; curated reproduction-view metrics are external to these three clean trees.

Use the preserved evaluator and its metric-availability records; no new metric was inferred.

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: Original 1000-cell smoke and baseline smoke/full/GAT smoke artifacts exist; size250 eight seeds evaluated. No new runtime reproduction.

Archived environment/prepare recipes and external original/reproduction checkouts. Size250 wrappers source missing Run_On_fir/activate_glue.sh; archive retains activate_glue.sh at a different path.

No smoke, help, status or validation mode was executed during this audit.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.

The separate [original reproduction archive](../../../historical/reproduction/README.md) preserves the older cluster recipes and eight compact metric YAMLs without reviving their activation or launch contracts.
