# Inherited upstream experimental suites

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Configured GLUE benchmarking, preprocessing/HVG/prior ablations and case studies.

## Dataset, architectures and conditions

Five configured RNA/ATAC datasets plus case-study-specific inputs.

Original GCN-GLUE plus configured external benchmark methods; five upstream case-study families.

Seed counts are expanded by workflow/utils.py; see the seven suite records and five case-study records below.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/workflow/Snakefile](../../../evaluation/workflow/Snakefile) |
| Configuration / manifest | [experiments/common/upstream_suites/config.json](config.json) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/workflow/rules/utils.smk](../../../evaluation/workflow/rules/utils.smk) |
| Plotting / reporting | [evaluation/workflow/scripts/benchmark.R](../../../evaluation/workflow/scripts/benchmark.R) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py upstream_suites --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**launch_blocker:** Historical upstream site profile uses gaog_g1/cn_icg/gpu_4l, not Fir; no local execution is established.

## Artifacts and metrics

O/evaluation/results/{raw,*.csv,*.pdf,umap_grid}; case studies emit stage directories under O/experiments/<case>/.

Inherited method-specific benchmarking and case-study metrics; thesis use is unverified.

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

Historical audit: Configured source; no verified local case-study model outputs. No new runtime reproduction.

Snakemake module support, Jupytext/Jupyter, R/packrat, prepared H5AD, genomes/annotations and optional external integration methods.



Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
