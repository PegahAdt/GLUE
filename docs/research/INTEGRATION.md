# Integration decisions and history

The release candidate starts at orchestration cleanup `649b9b8`, retaining the corrected 30-row PBMC dimension manifest. It composes source files deliberately rather than running an automatic code merge. The final integration commit preserves the original cleanup and architecture histories as parents (redundant ancestor parents are omitted); the original branch refs and worktrees remain unchanged. No local `main` branch existed at inspection; none is created or modified. Existing `master` is untouched.

The distinct original-GLUE reproduction branch is also retained in ancestry and indexed under `historical/reproduction/`, including its compact historical metrics.

The source trees are recorded in [the integration ledger](../../provenance/integration_sources.json), including destination, mode, original Git blob, SHA256 and decision. The root baseline scientific package and runner stay unchanged. Architecture packages/runners coexist in isolated directories. The PBMC GATED runner is distinct from the general GATED runner; only their identical model package is shared.

Existing configs, manifests, graph identities, metric YAMLs, freeze records and source hashes are byte-preserved. Experiment documentation is consolidated. Historical preservation notes are retained as literal `.md.txt` records when their links refer to an old checkout. Machine-specific scientific provenance is retained explicitly; it is not a portable default.

Old upstream CI/release payloads are archived under `historical/upstream_ci/` rather than enabled for fork package publication. Two expired signed download URLs are replaced in the current Muto documentation with a reference to its existing public CELLxGENE collection links. Originals remain in Git ancestry, with statically recorded 2021 expiries; history was not rewritten.

Existing architecture and experiment branches remain historical development lines. There are no new experiment branches. The integration branch can only become main after separate review and explicit approval. No GitHub push was performed.
