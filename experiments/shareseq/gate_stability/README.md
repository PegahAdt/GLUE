# SHARE-seq GATED gate stability

[Thesis map](../../../THESIS_EXPERIMENTS.md) · `REPRODUCIBILITY.md` (external, planned, or unresolved)

## Scientific objective

Are learned gates stable across initialization, model seeds and latent dimension?

## Dataset, architectures and conditions

Full paired Ma-2020 SHARE-seq, fixed cell order and fixed graph.

GATED-GLUE.

16 dimensions 16…4096 × gates .25/.50/.75/.95 × model seeds 0–2 = 192. A=144 (12 lower dimensions), B=48 (1536/2048/3072/4096); lam_keep=0.

## Implementation and configuration

| Stage | Source |
|---|---|
| Training | [evaluation/shareseq_gate_stability/experiment.py](../../../evaluation/shareseq_gate_stability/experiment.py) |
| Configuration / manifest | [experiments/shareseq/gate_stability/config.json](config.json) |
| Preprocessing | Not applicable / no entry point identified |
| Evaluation | [evaluation/shareseq_gate_stability/analyze.py](../../../evaluation/shareseq_gate_stability/analyze.py) |
| Plotting / reporting | [evaluation/shareseq_gate_stability/analyze.py](../../../evaluation/shareseq_gate_stability/analyze.py) |
| Canonical architecture bindings | `implementations/README.md` (external, planned, or unresolved) |

## Preserved design and freeze records

- [evaluation/shareseq_gate_stability/manifests/all_runs.csv](../../../evaluation/shareseq_gate_stability/manifests/all_runs.csv)
- [evaluation/shareseq_gate_stability/manifests/array_A.csv](../../../evaluation/shareseq_gate_stability/manifests/array_A.csv)
- [evaluation/shareseq_gate_stability/manifests/array_B.csv](../../../evaluation/shareseq_gate_stability/manifests/array_B.csv)
- [evaluation/shareseq_gate_stability/manifests/edges.csv](../../../evaluation/shareseq_gate_stability/manifests/edges.csv)
- [evaluation/shareseq_gate_stability/preflight.json](../../../evaluation/shareseq_gate_stability/preflight.json)

## Commands and execution boundary

From the repository root, inspect the catalog and this experiment without training or scheduler calls:

```bash
python3 -B experiments/launch.py --list
python3 -B experiments/launch.py share_gate_stability --dry-run
```

The default workspace is deliberately a placeholder. `environments/workspace.integration.example.json` (external, planned, or unresolved) binds the three canonical sources explicitly after its paths are replaced in an external copy. A printed historical/frozen plan is not an executable relocation adapter. Do not invoke archived wrappers against active runs.

**launch_blocker:** Frozen source hashes and absolute output paths bind the 192-run design to the preserved cluster workspace. Relocation requires a separately validated provenance adapter; do not rerun prepare over the frozen manifest.

## Artifacts and metrics

/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/dim_<d>/gateinit_<p>/seed_<s>/; analysis destination supplied to analyze.py.

Directed edge-aligned gate-threshold sets and pairwise Jaccard across seeds/dimensions/initializations; exact thresholds, empty-set convention and aggregation are in analyze.py.

`results/README.md` (external, planned, or unresolved) lists external outputs and included compact evidence. No numerical result was changed.

## Reproduction status and limitations

192 planned conditions; 139 retained checkpoint paths and matching Python-version/job provenance in the dated audits. Aggregate analysis incomplete; frozen portability blocked.

experiment.py imports full_dimension.py through sibling GLUE; preflight hashes bind source, environment, cell order, graph and edge-identity table. analyze.py requires all 192 COMPLETED.json records and exact edge alignment.



Historical paths, fingerprints and scientific configurations are retained. Frozen originals remain tied to their original workspace. Environment reconstruction, checkpoint compatibility and GPU convergence/numerical equivalence are unverified. Exact thesis section/figure correspondence requires the manuscript; no chapter or figure number is assigned here.
