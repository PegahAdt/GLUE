# PBMC graph evaluation and original-GCN controls preservation

This commit records the existing PBMC evaluation pipeline, original-GCN graph
subsampling control, separate randomized control, tests, documentation and
immutable configurations. Active source, graphs, manifests and submission
records remain byte-identical to their pre-preservation state.

The original-GCN control has retention fractions 1,.75,.5,.25,.1 and model seeds
0,1,2 with graph seed 0 (15 configurations). The separate randomized extension
adds model seeds 0,1,2 (three configurations). Original baseline source remains
at sibling GLUE commit `38726c508909e62a83326d2a7fed93dce438c8cb`.
No GATED model is substituted for the original GCN.

Source directories include their submission/dispatch scripts, and tests check
architecture identity, graph semantics, exact manifest identity, metric
definitions, seed alignment and mocked idempotent submission. The archived
completed GATED evaluator in randomized_control/validation is deliberate
source provenance; it is not an extra active evaluator or a model artifact.

The immutable settings/source-hash snapshot from the completed GATED report is
preserved separately as
`evaluation/pbmc_graph_perturbation/provenance/completed_evaluation_config.json`.
It contains evaluation settings and provenance, not metric scores. Its original
report-directory file is unchanged. Frozen inputs and graph verification JSON
remain at their original paths and are tracked explicitly despite broad ignore
rules. `preservation/source_manifest.tsv` records the selected original bytes.

## Scope and cluster dependencies

These scripts retain their absolute Fir paths, existing environment and prepared
input dependencies. Frozen metadata describes the historical completed GATED
comparison. Reconstructing a new experiment on another machine needs explicit
path/configuration preparation; these files are not a portable installer.

Graphs, datasets, completed report results, smoke artifacts, raw scheduler logs,
submission records, recovery archives and environments are excluded from this
commit. Existing thirteen inherited GATED launcher copies are already tracked
and still target GLUE_GATED; they were not edited or treated as new PBMC runs.

No training/evaluation was launched, no scheduler state was modified, no model
or manifest was changed, and nothing was pushed.

## Verified lightweight tests

The PBMC evaluator suite passed 16 cases. The original-GCN subsampling and
randomization suites passed 16 cases in an isolated process with the original
GLUE directory as PYTHONPATH, `--noconftest --import-mode=importlib`, CPU-only
visibility, disabled pytest plugins/cache and temporary outputs outside the
project. The repository-wide tests/conftest.py otherwise imports the gated
worktree's scglue before the original-GCN guard runs. A normal mixed invocation
was correctly rejected by that guard; active tests/conftest.py was not changed.

This invocation detail is a preserved test-harness limitation, not a change to
the original GCN model or experiment definitions. The separate SHARE validator
and stability unittest suite passed 14 cases. No training fit was launched.
