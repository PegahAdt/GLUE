# PBMC gcn graph randomization

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

How does guidance-graph structure affect integration under matched architecture and data?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

Original baseline GCN-GLUE.

three randomized controls + combined 18-row analysis joining the original 15-run retention design; graph seed0, model seeds0/1/2, dimension50. Retention helper floors fraction × reciprocal-pair count and uses nested subsets. Randomization requests ceil(10 × original relations) accepted double-edge swaps, with a bounded attempt counter.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/train.py](../../../evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/train.py) |
| Configuration / manifest | [experiments/pbmc/gcn_graph_randomization/config.json](config.json) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/evaluate.py](../../../evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/evaluate.py) |
| Plotting / reporting | [evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/gcn_report.py](../../../evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/gcn_report.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Preserved design and freeze records

- [evaluation/pbmc_graph_subsampling_gcn/randomized_control/manifest.csv](../../../evaluation/pbmc_graph_subsampling_gcn/randomized_control/manifest.csv)
- [evaluation/pbmc_graph_subsampling_gcn/randomized_control/combined_manifest.csv](../../../evaluation/pbmc_graph_subsampling_gcn/randomized_control/combined_manifest.csv)
- [evaluation/pbmc_graph_subsampling_gcn/randomized_control/validation/frozen_inputs.json](../../../evaluation/pbmc_graph_subsampling_gcn/randomized_control/validation/frozen_inputs.json)

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_gcn_randomized --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**launch_blocker:** Frozen cluster pipeline retained byte-for-byte. Its absolute-path/source-hash guards must be preserved; a fresh portable freeze and validated smoke are required before dispatch from a relocated checkout.

## Artifacts and metrics

Checkpoints: /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/results/10x-Multiome-Pbmc10k/randomized/graph_seed:0/model_seed:<s>/. Evaluator default: randomized_control/reports/full. Preserved batch explicitly overrides output to the parent pbmc_graph_subsampling_gcn/reports/combined_randomized_job_<SLURM_JOB_ID>/.

Graph-study-specific pairing/FOSCTTM, cell-type/modality integration, reference-neighbour, graph overlap/degree, gate and availability diagnostics. Exact definitions and N/A rules are in the preserved evaluator; do not interchange with the generic metric pipeline.

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: 3/3 trained; combined18-run evaluation waits on retention task7. No new runtime reproduction.

Shared reciprocal-edge helper P/evaluation/workflow/scripts/graph_perturbation.py; existing PBMC prepared inputs/graph. GCN evaluators import the GATED evaluator metric core but require gate-free original GCN models. GCN reference and evaluation settings are read from completed GATED report provenance at original absolute paths.

Completed-evaluator snapshot in randomized_control/validation is immutable scientific provenance; it is intentionally retained. Randomized submit_pipeline.py hardcodes original dependency 64840335; historical job numbers are not portable. Metadata dist attributes after rewiring are provenance, not new genomic distances.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
