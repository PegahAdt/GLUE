# GLUE experiment orchestration preservation

This branch preserves reviewed source and immutable experiment designs copied
from the Fir baseline checkout on 2026-11-10. Its parent is original GLUE
`38726c508909e62a83326d2a7fed93dce438c8cb`. No baseline model implementation was
changed. The original detached checkout remains at that commit and continues
to supply the datasets, environment and original GCN implementation used by
existing jobs.

## Preserved material

- GCN/GAT launchers, comparison/statistical analysis and manual-search source.
- Both historical GAT tuning workflow snapshots, including per-configuration
  workflows and exact parameter/target manifests. Repeated source files remain
  in place because scripts address their configuration-specific paths; Git
  deduplicates identical blobs. Generated jobs, logs and results are excluded.
- SHARE-seq preparation, training, matching, validation, gate extraction,
  full-data dimensions, evaluation and reporting source, plus immutable cell
  manifests and configuration/source-hash snapshots.
- PBMC gate-initialization evaluation/distribution-analysis source.
- Unique original-checkout environment/setup material under
  `historical/original_glue_checkout/`. Its `env.yaml` preserves the local
  msrest 0.5.5 specification; the original file was not changed.

`preservation/source_manifest.tsv` records each source path, preserved relative
path, SHA256, size and classification. It is a preservation ledger, not a run
manifest. Configuration files were copied byte-for-byte, including CRLF where
present. Scores, embeddings, checkpoints and generated figures are excluded.

## Historical constraints; do not relaunch unchanged

These are source snapshots, not portable standalone launch instructions.
Existing scripts intentionally retain their original absolute Fir paths.
Several GAT rules call `workflow/scripts/run_GLUE.py` relative to the original
working directory, while the current detached baseline runner has no GAT CLI.
Historical tuning workers also pin an earlier GAT commit. This preservation
branch does not repair those paths or update commit pins. The manual GAT
search's feature-reference choice also needs scientific review before use.

The existing shared environment is `../GLUE/conda`, source datasets are under
`../GLUE/data/dataset`, and architecture implementations remain in sibling
GLUE_GAT and GLUE_GATED worktrees. Some preserved preflight snapshots depend on
those sibling paths and source hashes. They record the historical run design;
they are not new validation or submission records.

Original input/result paths, source/configuration hashes, and Slurm records
were not changed. No jobs were submitted or cancelled and no branch was pushed.
Future portability, launcher repairs, experiment execution and publication
are separate review steps.
