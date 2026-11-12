# PBMC learned edge analysis

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Which prior edges are down-weighted and how stable are gates across subsamples?

## Dataset, architectures and conditions

PBMC 10x Multiome: paired human PBMC scRNA-seq + scATAC-seq.

Read-only scientific analysis of ten historical GATED models.

Full reference plus 3 sizes × 3 subset seeds, all model seed 0; no new model design.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | Not applicable / no entry point identified |
| Configuration / manifest | [experiments/pbmc/learned_edge_analysis/config.json](config.json) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/extract_gated_edge_analysis.py](../../../evaluation/extract_gated_edge_analysis.py) |
| Plotting / reporting | [evaluation/gate_analysis/build_gated_edge_analysis_report.py](../../../evaluation/gate_analysis/build_gated_edge_analysis_report.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_gate_analysis --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**launch_blocker:** Analysis-only workflow: preserved report generator has fixed historical source/output paths; no new training design.

## Artifacts and metrics

G/evaluation/gate_analysis/: gates_<model>.csv, gate_distribution_summary.csv, ranked/suppressed-edge/correlation tables, gate_stability_size*.csv and TeX report.

This analysis extracts learned directed-edge gate values, topology-aligned edge metadata and gate diagnostics from existing GATED checkpoints. The exact distribution/edge-comparison summaries are defined by `extract_gated_edge_analysis.py` and `build_gated_edge_analysis_report.py`; no new integration metric or training task is introduced.

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: Ten reused models analyzed; generated reports excluded. No new runtime reproduction.

Requires final.dill, original graph topology, gate diagnostics and model sources from GATED comparison. Checkpoint deserialization would import model dependencies and was not attempted.

Report builder reads precomputed CSVs; it is not a second model/evaluation implementation.

Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
