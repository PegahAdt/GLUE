# GLUE research experiments

Start with the experiment catalog. The orchestration branch retains original GCN source from `38726c5`. The GAT and GATED implementations live on separate branches.

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py pbmc_dimensions --dry-run
python3 -B experiments/launch.py share_dimensions --dry-run --task 35
```

Read the experiment README before execution. `catalog.json` separates actual designs, historical
views, unexecuted plans, frozen pipelines and architecture-only implementations. Designs overlap:
reused references and analysis views must not be summed as new training runs. All current status
claims are dated November 10, 2026 and supported by the external cleanup report and its audit evidence.

Copy `workspace.example.json` outside the checkout and bind your actual Python environment,
architecture checkout paths, prepared inputs and fresh output directory. The example uses
placeholder paths and cannot submit. Partition names are explicit examples from Fir; choose your
own cluster partition. Source fingerprints enforce the architecture/runner versions. `--dry-run`
is the default and makes no directories, environment activations or scheduler calls. It prints an
array-to-configuration mapping and submission commands. `--submit` is the single dispatch route;
it reserves an exclusive external record before the first sbatch and preserves partial submissions
for manual review. Training/evaluation arrays use afterok. Existing outputs are never overwritten.

Portable command construction is lightly tested, not a claim of successful GPU reproduction.
Frozen graph-control and SHARE-stability designs remain blocked for relocated dispatch until
their absolute-path integrity freezes have a validated adapter. Their original source, manifests,
fingerprints, job histories and active paths remain intact. The generic evaluator reports cell
integration (and explicit feature consistency where configured); gate extraction and aggregate
scientific reports remain separate named analysis stages. Do not label integration completion as
completion of those analysis stages.

The `evaluation/` implementation locations remain where frozen provenance or scripts depend on
them. They are indexed by experiment rather than copied into a second code tree. Exact historical
workflow copies are factored into `common/workflow_templates/` plus `workflow_snapshots.json`.
Restore any old workflow byte-for-byte into a new external directory with
`common/restore_workflow.py ORIGINAL_WORKFLOW_PATH NEW_DIRECTORY`. Restoration does not repair
historical GAT relative-runner/commit-pin problems. Historical wrappers are provenance, not an
alternative current dispatch interface.

See `REPRODUCIBILITY.md`, `HISTORICAL_SUBMISSIONS.md` and each experiment README for scientific
settings, source dependencies, expected counts, historical resource overrides and remaining limits.

## Original GLUE case studies

## Case studies

* TripleOmics: Triple omic integration of scRNA-seq, scATAC-seq and snmC-seq in the mouse cortex
* RegInf: Regulatory inference in PBMC via integrating scRNA-seq, scATAC-seq along with pcHi-C and eQTL
* Atlas: Mega-scale scRNA-seq, scATAC-seq integration of a human cell atlas

## Execution

Go to the subdirectories for each case study, and execute:

```sh
snakemake --use-conda --res mutex=1 -j20 -prk
```
