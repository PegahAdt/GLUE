# Reproducing the GLUE experiments

Choose an experiment with `python3 -B experiments/launch.py --list`. Each experiment README gives its design, source paths, status and limitations. The shared launcher prints the selected task, exact runner arguments, resource requests and dependency plan by default. Use `--task N` to inspect a particular array index.

## Source checkouts and environment

Use the orchestration cleanup branch for the catalog and shared launcher. For the original GCN runner, use the unchanged source from commit `38726c508909e62a83326d2a7fed93dce438c8cb`. The orchestration checkout also contains that exact model and runner. Use `GAT_GLUE` at `71e15179a48adc295bf9068d6d483ff928a2db76` for raw-weight GAT, including the GCN mode used in the PBMC dimension sweep. Use the GATED cleanup checkout for the static gated encoder. The PBMC graph checkout owns the perturbation workflow and its original GCN controls. The normalized GAT implementation remains on `GAT_NORM_GLUE` at `5ac0b073a5f0a372a472605d8fc61a39def55b31`.

`common/architecture_sources.json` records the architecture and runner file hashes. The launcher verifies them before dispatch and on compute nodes. The checkout paths in the example are placeholders. Point them to the actual checkouts on your cluster and bind the Python executable from a GLUE 0.2.0-compatible environment. The Fir environment used for the CPU checks was `GLUE/conda` with Python 3.8. Historical environment recipes, including R and BEDTools setup, are under `historical/original_glue_checkout/`. See the parent repository's installation instructions for upstream dependencies. Fresh environment creation and GPU compatibility were outside the lightweight validation.

## Data and provenance

| Dataset | Cells per modality | RNA features | ATAC features | Prepared input provenance |
|---|---:|---:|---:|---|
| 10x Multiome PBMC | 9,631 | 29,095 | 107,194 | Original collection under `data/`. Subset sizes, seeds and matched graph paths come from the preserved target lists and experiment manifests. |
| Ma-2020 SHARE-seq mouse skin | 32,231 | 21,478 | 340,341 | `evaluation/shareseq_ma2020/scripts/prepare.py`, ordered cell manifests, preflight hashes and recorded PCA/LSI references. |

Start with the data acquisition and preprocessing rules under `data/` and `evaluation/workflow/`, or use verified copies of the historical prepared inputs. Keep raw data, prepared H5AD files, graphs, checkpoints, embeddings and logs outside Git. The ordered cell identifiers and SHARE edge identity table are small immutable design inputs. Configuration CSV, TSV and JSON files are tracked. Existing compact metric YAMLs retain their role as historical results.

Copy `workspace.example.json` outside the repository, then specify the Python executable, architecture paths, Slurm partitions, an external output root, and path bindings for your prepared inputs. A binding maps an original provenance prefix to your local copy. The longest matching prefix wins. `repo:` bindings are relative to the orchestration checkout. Keep historical inputs read-only. For SHARE, copy the PCA/LSI files named in `shareseq/unirep_references.json` or regenerate and verify matching fingerprints. The launcher checks the recorded input and representation digests. PBMC GAT comparison and tuning retain their own recorded prepared-input paths.

## Launch and inspect

```bash
python3 -B experiments/launch.py share_matched_cells --workspace /path/to/workspace.json --dry-run --task 17
```

Inspect every relevant array index and output directory before a compute smoke test. `--phase train` and `--phase evaluate` select one phase. `--phase all` plans training followed by evaluation with an `afterok` dependency. The `--submit` switch dispatches supported plans. The external `submission.json` records reservations and accepted jobs. If a scheduler reply is ambiguous, inspect the reservation and the scheduler before any retry. The launcher checks that the workspace and design files match the versions hashed when it submitted the job. It refuses to overwrite existing runs.

Training outputs appear under `<output_root>/<experiment>/runs/<task_id>/`. Metrics appear in the corresponding `metrics/<task_id>/`. A reused row reads a historical run through the configured bindings. For architecture comparisons, task 0 trains the full feature reference. Evaluation starts at task 1. PBMC Stage A GATED tuning uses its original prepared datasets for metrics and defers feature consistency. Non-50D PBMC dimension rows likewise defer feature consistency. The PBMC gate initialization study uses the preserved 50D GATED full feature reference.

SHARE integration validates paired observations and the eight original metric definitions. Gate extraction and aggregated reports have separate preserved entrypoints listed in the experiment README. The gate-stability sweep and original GCN graph controls still require their cluster-specific provenance and validation pipeline. Their canonical catalog plans identify the existing batch files and frozen manifests. Relocated execution remains unavailable until the integrity checks can be validated against a fresh workspace. The historical GAT manual search and tuning evaluation have unresolved feature-reference questions. The clean GAT training commands select the correct architecture runner and passed parser/import checks. The historical Snakemake launchers retain their relative-runner and commit-pin problems.

The [historical submission inventory](HISTORICAL_SUBMISSIONS.md) records the original scripts and effective resource overrides. To recover the exact old workflow files, use the preservation parent or the checksum-verified restoration tool.

```bash
python3 -B experiments/common/restore_workflow.py \
  evaluation/gat_tuning_10x/screen_v2/configs/lr_0p001/workflow \
  /path/to/new-empty-destination
```
