# Validation scope

Repository consistency and scientific reproduction are separate. Integration validation checks pinned package/runner hashes, original configuration/manifests/metric bytes, source routes, architecture isolation, 30-condition PBMC dimension coverage, catalog/document mappings, links, syntax, source history, secret/artifact patterns and original-worktree preservation. Safe CPU regression checks cover the mocked canonical planner/restorer and synthetic graph invariants; they do not run real experiments.

The generated repository validation record is [provenance/validation_summary.json](../../provenance/validation_summary.json). The integration worktree's final commit/hash and original-worktree snapshot comparison are recorded in the external integration review evidence; a commit cannot embed its own hash without changing that hash.

## Inherited exceptions and external dependencies

The upstream `experiments/RegInf/s06_genomic_tracks.py` contains an empty `if` suite around line 66. It is retained byte-for-byte and explicitly excluded from an all-Python-syntax-pass claim. The existing `.vscode/launch.json` is JSONC, not strict JSON. No scientific fix is hidden in this integration.

The symlinks `evaluation/custom` and `experiments/Atlas/custom` resolve to the tracked `packrat/custom` placeholder directory, which contains only `.gitignore` in this checkout. Installed R packages are an external dependency; the links were not silently replaced with the different `custom/` source-archive directory. Other historical wrappers retain broken archive/cwd/activation references. They are not presented as current executable commands. [The integration map](../../provenance/integration_sources.json) and experiment READMEs distinguish preserved historical source from the current planner.

Inherited upstream README/RST/notebook documentation can retain upstream context or missing external assets. New thesis documentation and its local code links are validated separately; unresolved inherited references are listed in the validation record rather than silently rewritten. Source-level import/path guards are inspected but their successful runtime execution is not asserted.

## Not verified

No GPU computation, CUDA/driver compatibility test, training, experiment evaluation, dataset download, package/environment installation or activation, Slurm submission/cancellation, remote connection or GitHub push was performed. GPU convergence, checkpoint loadability, metric/figure regeneration, scientific ranking, raw-data preprocessing, Nibi migration and full thesis correspondence remain unverified.

## Historical whitespace

The reviewed staged diff contains 102 whitespace diagnostics in byte-preserved imported source/history files. New research documentation and integration helper code introduced none. These cosmetic diagnostics were retained to preserve scientific and historical file identity; they are not reported as a clean `git diff --check` result.
