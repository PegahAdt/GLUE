# Research experiments

Start with the orchestration branch's `experiments/catalog.json` and `experiments/README.md`.
The original model implementation remains in `scglue/`; architecture branches stay separate.
The `evaluation/` paths are retained where frozen provenance or historical tools depend on them.
They are implementation/provenance paths, not additional canonical submission choices.
Use the experiment directory's README and the shared launch planner. Read blockers before execution.
Do not run historical wrappers against active research directories.

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
