# Planned adaptive GAT search

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Can a five-candidate screen followed by four validation runs improve integration?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

Raw-prior GAT-GLUE; adaptive plan only.

Five candidates at 2,000 cells/subset seed 0/model seed 0; chosen winner validates (2000,1),(2000,2),(250,0),(8000,0).

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/run_gat_manual_search.py](../../../evaluation/run_gat_manual_search.py) |
| Configuration / manifest | [experiments/pbmc/gat_manual_search/config.json](config.json) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/run_gat_manual_search.py](../../../evaluation/run_gat_manual_search.py) |
| Plotting / reporting | Not applicable / no entry point identified |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_gat_manual --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**launch_blocker:** Historical manual search uses an unmatched feature reference. Adaptive winner selection must not be precomputed or silently repaired during cleanup.

## Artifacts and metrics

O/evaluation/results_gat_manual_search/<candidate>/<size-and-seed>/…; search_summary.json is intended winner record.

Use the preserved evaluator and its metric-availability records; no new metric was inferred.

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Adaptive plan/source retained; finalized execution and feature-reference policy unresolved.

SOURCE uses tuning graph_0p05 raw inputs; REFERENCE_FEATURE selects a default graph .02/align .05 full model. Rank combines nine metrics including feature consistency, so reference choice can affect winner selection.

Candidate graph/align pairs (.04,.05),(.05,.04),(.05,.05),(.05,.06),(.06,.05), all slope .10 and LR .002. No independent reporting entry point identified; script writes winner JSON.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
