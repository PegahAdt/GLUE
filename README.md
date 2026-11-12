# GLUE Graph Architectures and Guidance-Graph Robustness

MSc research on how graph neural network architectures and guidance-graph structure affect single-cell multi-omics integration. This repository extends **Gao Lab's GLUE**; it does not claim authorship of the original framework.

The research asks whether learned graph attention or static edge-retention gates improve the use of a potentially imperfect guidance graph, and how architecture, training-cell count, latent dimension and graph perturbations affect integration and learned-edge stability. Datasets are paired RNA/ATAC PBMC and mouse-skin SHARE-seq. No unsupported performance ranking or biological-causality claim is made here.

**This is the `integration/thesis-release-candidate` branch: a proposed research landing branch, not an approved replacement for main.** Repository consistency has a separate validation record; GPU reproduction, migration and scientific completeness remain unverified. All historical source implementations and scientific configurations are preserved.

## Start here

| Question | Guide |
|---|---|
| What changed relative to upstream GLUE? | [Contributions and authorship evidence](CONTRIBUTIONS.md) |
| How do GCN, GAT and GATED differ? | [Architecture and isolated implementations](ARCHITECTURE.md) |
| Which experiment supports each research question? | [Thesis-to-code map](THESIS_EXPERIMENTS.md) |
| How do I inspect or reconstruct an experiment? | [Reproducibility guide](REPRODUCIBILITY.md) and [experiment catalog](experiments/README.md) |
| Where are the existing results and figures? | [Artifact index](results/README.md) |
| What can be checked without GPUs? | [Validation scope](docs/research/VALIDATION.md) |
| What is inherited and how is it licensed? | [License and attribution](LICENSE_AND_ATTRIBUTION.md) |

## Research contributions

- A signed, prior-weighted GAT encoder within the existing GLUE variational/adversarial framework.
- Static trainable GATED edge-retention probabilities, topology-aligned model state and gate diagnostics.
- Matched architecture/data-size/dimension studies, gate-initialization and stability investigations, and PBMC guidance-graph retention/randomization controls.
- A shared experiment registry, explicit source fingerprints, guarded planning/dispatch, frozen provenance and experiment-specific evaluation/reporting.

Git history supports the architecture modifications under Pegah Aryadoost's author identity. Bulk-preserved scripts do not establish sole line-level authorship. See the evidence and limitations in [CONTRIBUTIONS.md](CONTRIBUTIONS.md).

## Repository organization

```text
scglue/                   Original GCN-GLUE package, unchanged
implementations/          Pinned GAT/GATED/normalized-GAT packages and distinct PBMC runner
experiments/              PBMC/SHARE-seq designs, manifests and shared planner
evaluation/               Shared metrics, graph utilities and preserved study pipelines
data/                     Upstream acquisition/preprocessing recipes; no prepared datasets
environments/             Evidence-based environment notes and non-installable observations
results/README.md         Index of external results and figures
provenance/               Source hashes, integration decisions and experiment mappings
scripts/                  Standard-library repository validation
tests/                    Upstream, graph-control and repository checks
historical/               Factored workflow history, historical notes and upstream CI
docs/                     Upstream API docs, GATED math note and research documentation
```

Original workflow paths are retained where source/provenance depends on them. Experiments are organized as directories; there is no need to check out an experiment branch to read the thesis-focused code. The original architecture/development branches remain available as historical development lines, including the distinct [original reproduction archive](historical/reproduction/README.md). The 880 factored historical workflow files are not expanded back into this tree.

## Safe inspection

From the repository root, with standard-library Python:

```bash
python3 -B scripts/validate_release.py
python3 -I -B experiments/common/test_launch.py
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_dimensions --dry-run --task 27
```

These checks/plans do not run an experiment or contact Slurm. The launcher defaults to dry-run; execution requires an external workspace, verified inputs, a compatible environment and explicit submission. [REPRODUCIBILITY.md](REPRODUCIBILITY.md) explains the boundaries. Installing published `scglue` alone does not select the GAT or GATED source.

## Current scientific limits

The PBMC dimension registry contains all 30 conditions, including six reused 50D references. Dedicated original-GCN graph controls use the baseline implementation; fresh PBMC dimension GCN rows use the GAT branch in GCN mode. These are distinct source roles.

Matched SHARE GCN evaluation coverage, full gate-stability analysis, historical per-run source/environment provenance and frozen-pipeline relocation remain incomplete or unverified. A dedicated SHARE guidance-edge-subsampling study was not located; SHARE cell subsampling is a different intervention. No thesis manuscript was supplied, so exact chapter/figure correspondence is pending.

## Attribution

Original GLUE: Gao Lab, [upstream repository](https://github.com/gao-lab/GLUE), [original project preprint](https://doi.org/10.1101/2021.08.22.457275). The upstream MIT [LICENSE](LICENSE) is retained. Bundled third-party packages retain their own notices; see [LICENSE_AND_ATTRIBUTION.md](LICENSE_AND_ATTRIBUTION.md).
