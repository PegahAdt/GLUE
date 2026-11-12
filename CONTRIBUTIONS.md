# Contributions relative to upstream GLUE

## Upstream foundation

Gao Lab developed GLUE's graph-linked variational integration framework, modality encoders/decoders, feature/graph reconstruction, adversarial alignment, baseline graph convolution, shared metric implementations, acquisition recipes and original benchmarks/case studies. The original MIT notice and historical ancestry are retained. This repository does not claim those components as new MSc work.

The original model/runner at `38726c508909e62a83326d2a7fed93dce438c8cb` remains at the repository root. Its scientific files are byte-identical to the orchestration source pin. See [architecture versions](provenance/implementation_versions.json).

## Architecture modifications supported by Git/source evidence

| Contribution | Independently inspectable evidence | Authorship limit |
|---|---|---|
| Signed prior-weighted GAT | Commit `71e15179a48adc295bf9068d6d483ff928a2db76`; [attention module](implementations/gat/scglue/models/nn.py), [encoder](implementations/gat/scglue/models/sc.py), [runner](implementations/gat/evaluation/workflow/scripts/run_GLUE.py) | Git records Pegah Aryadoost as author; identity metadata does not prove exclusive intellectual or line-level authorship |
| Static GATED encoder and keep penalty | Development commits `9c8e7e8` and `4cbbd32`; preserved [encoder](implementations/gated/scglue/models/sc.py), [trainer/model](implementations/gated/scglue/models/scglue.py), [tests](implementations/gated/tests/models/test_gated_graph.py) | Git author identity matches the research branch; later preservation commits collect historical work without establishing original dates for every copied file |
| Normalized-prior GAT option | Commit `5ac0b073a5f0a372a472605d8fc61a39def55b31`; [source](implementations/gat_normalized/scglue/models/sc.py) | Implementation exists; no thesis experiment or result is inferred |

GAT is a single-head signed, prior-weighted attention mechanism within GLUE. GATED learns topology-aligned global edge-retention probabilities with fixed self-loop gates and no coefficient renormalization. Neither replaces the upstream cell encoders, likelihood model, feature space or adversarial framework. [ARCHITECTURE.md](ARCHITECTURE.md) explains the exact distinctions.

## Guidance-graph robustness

The [PBMC graph helper](evaluation/workflow/scripts/graph_perturbation.py) supports nested reciprocal gene–peak edge retention and degree-preserving double-edge randomization, preserving nodes, self-loops and paired edge attributes. Graph seed and model seed have separate meanings. Fixed graph seed zero does not estimate variation across perturbed-graph seeds. Rewired metadata such as original distance is retained provenance, not a recomputed genomic distance.

The [GATED perturbation study](experiments/pbmc/gated_graph_perturbation/README.md) is compared with [original-GCN retention controls](experiments/pbmc/gcn_graph_subsampling/README.md) and [randomized controls](experiments/pbmc/gcn_graph_randomization/README.md). The source/tests are verifiable; frozen execution and evaluator provenance still constrain relocation. No dedicated SHARE graph-edge-retention design was located, so related SHARE cell-size studies are not relabeled as graph perturbations.

## Experimental and research-engineering work

The consolidated catalog covers architecture comparisons, matched training-size designs, latent-dimension sweeps, gate initialization/stability, learned-edge analysis, graph controls and clearly labeled plans. It records immutable manifests, source fingerprints, reused references, guarded submission reservations and explicit phase dependencies. Consolidation preserves 880 historical workflow paths through a template/restore manifest instead of expanding duplicates.

The PBMC 30-condition coverage correction adds three already-existing 8,000-cell/50D references without new fits or metric changes. Safe structural tests verify that reused references return before scientific execution. Evaluation/reporting utilities are preserved with their exact metric/reference policies, including unresolved differences.

The cleanup/integration and documentation include assisted research-engineering work; they are not evidence that every historical script was independently authored by the thesis researcher. Bulk preservation, generated manifests and inherited utilities are distinguished in [source provenance](provenance/integration_sources.json) and [the thesis map](THESIS_EXPERIMENTS.md).

## Limitations

No manuscript was available for exact thesis chapter/figure lineage. Some reused checkpoint source commits and per-run package stacks remain unknown. GAT feature-reference policy, GATED Stage-A representation choices, incomplete matched SHARE metrics, incomplete stability/graph coverage and frozen portability remain documented gaps. Repository integration does not establish numerical equivalence, convergence, superiority or biological causality.
