# Reproducing the research

## What this repository establishes

The scientific source, configurations, manifest rows, compact tracked metrics and frozen provenance are preserved. Structural checks and mocked launcher/synthetic graph tests establish repository consistency only. They do not establish checkpoint validity, CUDA compatibility, convergence, numerical equivalence or the completeness of thesis results.

Begin with [THESIS_EXPERIMENTS.md](THESIS_EXPERIMENTS.md), then the relevant experiment README. [results/README.md](results/README.md) identifies external historical artifacts; no raw/prepared datasets, checkpoints, embeddings, generated logs or thesis PDFs are bundled. Exact thesis figure/table mapping requires manuscript verification.

## Source and environment selection

The root `scglue` is original GCN. GAT, GATED and the separate PBMC graph runner are selected explicitly through [implementation directories](implementations/README.md). Keep each architecture in a separate process. A published `scglue` version label does not identify a fork. Never silently substitute current sources for an old serialized model.

[Environment recovery](environments/README.md) distinguishes Run-verified, Environment-observed, Source-declared, Inferred and Unknown versions. A shared observed Python environment supports all core architectures, but no installable cross-cluster recipe is asserted. R/packrat and system tools are additional requirements when rebuilding preprocessing. Do not execute historical installation/activation scripts merely to inspect versions.

## Inputs and configurations

Use the original dataset acquisition/preprocessing recipes under [data/](data/README.md) and [evaluation/workflow/](evaluation/workflow/Snakefile), or verified copies of the historical prepared RNA/ATAC, guidance graph and cached PCA/LSI representations. Genome assets and Ma author-supplied celltype annotations are external dependencies. Their availability and redistribution rights are not implied by public code.

Manifest scientific settings are unchanged. Subset seed, model seed, graph seed, architecture and implementation are different fields. PBMC dimensions have 30 conditions, with six saved 50D references reused. Fresh dimension GCN fits use GAT-in-GCN mode; original-GCN graph controls bind the baseline package. Analysis views overlap and must not be summed as independent runs.

## Safe planning

From the repository root:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_dimensions --dry-run --task 27
python3 -B experiments/launch.py share_dimensions --dry-run --task 35
```

The existing default workspace is a non-executable placeholder. Copy [environments/workspace.integration.example.json](environments/workspace.integration.example.json) to a new location outside the checkout and replace every placeholder with verified architecture, environment, input, partition and fresh output paths. Source digests are checked before supported dispatch. The planner defaults to dry-run and does not create outputs or call the scheduler. No submission command is prescribed until environment/input/resource contracts are validated.

`--phase train`, `--phase evaluate` and `--phase all` select supported phases. Existing checkpoints/outputs are never overwritten. A full comparison reference can be required by evaluation even if it is not an independently evaluated row. GAT tuning/manual feature-reference policy is unresolved. GATED Stage A uses its historical prepared representations; do not silently replace them with another evaluation reference.

## Frozen and historical pipelines

SHARE gate stability, PBMC GATED graph perturbation and original-GCN graph controls preserve original paths, commits, input/source hashes, edge ordering and historical dependencies. Their source is included for inspection, but **relocated execution is blocked or unverified**. Editing freezes, reusing old dependency IDs or pointing a preserved wrapper at this integration checkout is not a validated migration method.

Historical configured workflows can be recovered into a fresh external directory with the existing checksum-verifying [restore tool](experiments/common/restore_workflow.py). Restoration is not repair: historical GAT runner/commit bindings and missing activation context remain historical limitations. No frozen source or original job was modified during integration.

## Evaluation and results

The generic integration evaluator emits eight metrics; feature consistency is a separately configured calculation. Graph studies use their own pairing, graph/gate diagnostics and availability policy. SHARE gate-stability analysis requires exact directed-edge alignment and the required completed run set. Do not substitute one evaluator merely because metric names overlap.

Dated audit gaps include missing matched SHARE GCN metric files, incomplete 192-condition stability coverage, incomplete original-GCN retention coverage, unknown older checkpoint source revisions and unlocated dedicated SHARE graph-retention results. The small tracked PBMC dimension YAMLs are historical evidence, not rerun results.

## CPU-only repository checks

```bash
python3 -B scripts/validate_release.py
python3 -I -B experiments/common/test_launch.py
python3 -I -B tests/repository/test_release.py
```

The graph helper additionally has synthetic tests at `evaluation/tests/test_graph_perturbation.py`, requiring existing NumPy, NetworkX and pytest. They do not load data, import GLUE, train, evaluate real experiments or contact Slurm. Avoid blanket pytest collection: other preserved tests load model/data/frozen contexts and are not part of this safe check set. No dependency installation is required or authorized by these commands.

See [validation scope and inherited limitations](docs/research/VALIDATION.md). The upstream RegInf empty-suite syntax defect remains in historical source. No GPU reproduction was performed.
