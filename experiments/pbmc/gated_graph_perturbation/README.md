# PBMC gated graph perturbation

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

How does guidance-graph structure affect integration under matched architecture and data?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

GATED-GLUE.

six conditions × model seeds 0–2: original, retain .75/.50/.25/.10, degree-preserving randomized; graph seed0, model seeds0/1/2, dimension50. Retention helper floors fraction × reciprocal-pair count and uses nested subsets. Randomization requests ceil(10 × original relations) accepted double-edge swaps, with a bounded attempt counter.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/pbmc_graph_perturbation/run_array.sbatch](../../../evaluation/pbmc_graph_perturbation/run_array.sbatch)<br>[implementations/gated_pbmc/evaluation/workflow/scripts/run_GLUE.py](../../../implementations/gated_pbmc/evaluation/workflow/scripts/run_GLUE.py) |
| Configuration / manifest | [experiments/pbmc/gated_graph_perturbation/config.json](config.json) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/pbmc_graph_perturbation/scripts/evaluate.py](../../../evaluation/pbmc_graph_perturbation/scripts/evaluate.py) |
| Plotting / reporting | [evaluation/pbmc_graph_perturbation/scripts/reporting.py](../../../evaluation/pbmc_graph_perturbation/scripts/reporting.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Preserved design and freeze records

- [evaluation/pbmc_graph_perturbation/manifest.csv](../../../evaluation/pbmc_graph_perturbation/manifest.csv)
- [evaluation/pbmc_graph_perturbation/provenance/completed_evaluation_config.json](../../../evaluation/pbmc_graph_perturbation/provenance/completed_evaluation_config.json)

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_gated_graph --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**launch_blocker:** Frozen cluster pipeline retained byte-for-byte. Its absolute-path/source-hash guards must be preserved; a fresh portable freeze and validated smoke are required before dispatch from a relocated checkout.

## Artifacts and metrics

/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_perturbation/results/10x-Multiome-Pbmc10k/<condition>/graph_seed:0/model_seed:<s>; reports/full/{per_run_metrics,summary_metrics,baseline_comparison,metric_availability,graph_statistics}.csv plus figures/report. Randomized GCN run directories actually live in the parent original-GCN results tree, as recorded in its manifest.

Graph-study-specific pairing/FOSCTTM, cell-type/modality integration, reference-neighbour, graph overlap/degree, gate and availability diagnostics. Exact definitions and N/A rules are in the preserved evaluator; do not interchange with the generic metric pipeline.

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: 18 trained and evaluated. No new runtime reproduction.

Shared reciprocal-edge helper P/evaluation/workflow/scripts/graph_perturbation.py; existing PBMC prepared inputs/graph. GCN evaluators import the GATED evaluator metric core but require gate-free original GCN models. GCN reference and evaluation settings are read from completed GATED report provenance at original absolute paths.

Full evaluation is CPU Slurm work but is prohibited in this audit. Fixed graph_seed=0 means these designs do not assess variation across graph seeds.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
