# Environment evidence and workspace bindings

**No installable environment recipe is asserted.** [Observed Python metadata](observed_python_stack.json) records exact package versions/builds with classified source hashes and lines from preserved Fir metadata. Those files are not a new solve/lock and the original binary environments are external.

[Run-linked evidence](run_version_evidence.json) records original job IDs, external relative paths and inspected log/provenance hashes. Run-verified: Python 3.8.5 is explicitly logged for 139 retained SHARE gate-stability jobs whose IDs match saved provenance. Environment-observed: the two preserved prefixes have matching inventories including PyTorch 1.10.1, toolkit 11.3.1 and a torch CUDA build field of 11.3. A driver-reported maximum CUDA version is a different fact. The exact package stack of every thesis run is not recovered by observing a current prefix.

Three Conda/distribution version-label discrepancies remain in legacy-api-wrap, requests-cache and setuptools. Their cause/effective import versions were not resolved. No PyTorch Geometric or extension-wheel dependency is required by the inspected core paths; native torch scatter operations are not a torch-scatter requirement.

Source-declared: the preserved [env.yaml](../env.yaml), [pyproject.toml](../pyproject.toml) and [packrat lock](../packrat/packrat.lock). The old export strips binary-build precision and comments CUDA/scglue fields; do not treat it as a verified reconstruction of the observed binaries. The lock's R 4.0.2 profile differs from a later R 4.3.1 setup attempt. Both inspected later user libraries lack key Seurat/Signac/DoubletFinder DESCRIPTION metadata and historical setup logs report dependency failures. Do not merge these profiles into an invented working R environment.

Inferred: one shared Python package profile can serve GCN/GAT/GATED and evaluation/plotting with separate source bindings. Unknown: Nibi platform/driver/GPU compatibility, ABI/serialization behavior, complete raw-preprocessing R provenance and old per-run source revisions. No environment was activated, rebuilt or installed during integration.

Use [workspace.integration.example.json](workspace.integration.example.json) as a non-executable template. Copy it outside the repository and replace every `/replace-me` path, partition and protected input root. The scientific fields remain in the unchanged experiment manifests. Original machine-specific paths in those manifests are provenance and require explicit path bindings; frozen guards are not bypassed by the template.
