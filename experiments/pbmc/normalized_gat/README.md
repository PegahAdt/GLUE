# Normalized guidance-edge GAT variant

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

How would normalized rather than raw prior weights affect GAT?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

Normalized-prior GAT variant; architecture option without a local scientific experiment manifest.

Runner defaults exist; no experiment seeds or dataset/task mapping specified.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [implementations/gat_normalized/evaluation/workflow/scripts/run_GLUE.py](../../../implementations/gat_normalized/evaluation/workflow/scripts/run_GLUE.py) |
| Configuration / manifest | [experiments/pbmc/normalized_gat/config.json](config.json) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | Not applicable / no entry point identified |
| Plotting / reporting | Not applicable / no entry point identified |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py gat_normalized --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**launch_blocker:** No experiment manifest or verified execution; do not invent a scientific configuration.

## Artifacts and metrics

No experiment-specific output contract identified; generic runner could emit standard latents/checkpoints if a design were created.

No experiment-specific metric/result contract established.

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Implementation and test source only; no verified thesis experiment manifest or results.

Separate GAT_NORM_GLUE branch, not the raw-prior GAT source pinned by the clean catalog fingerprints.



Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
