# GATED GLUE Experiment Results

Large experimental outputs are stored on the Fir cluster and are not tracked in Git because they contain large model checkpoints, embeddings, intermediate files, and logs.

The paths below are relative to:

`/project/6001426/paa40/GlUE_Exp/GLUE_GATED/`

## 1. Embedding Dimension Sweep

**Results:**  
`evaluation/results_dimension_sweep/`

**Experiment setup:**  
Tests GATED GLUE across different latent embedding dimensions to determine how embedding size affects integration performance.

**Experiment/workflow files:**  
`evaluation/dimension_sweep/`

---

## 2. Gate Initialization Sensitivity

**Results:**  
`evaluation/results_gate_init_sensitivity/`

**Experiment setup:**  
Tests different initial gate values and random seeds to determine whether learned gates and downstream integration performance are sensitive to gate initialization.

**Experiment/workflow files:**  
`evaluation/gate_init_sensitivity/`

---

## 3. GATED Hyperparameter Tuning

**Results:**  
`evaluation/results_gated_tuning/`

**Experiment setup:**  
Hyperparameter search for the GATED GLUE architecture, including staged tuning runs used to identify promising GATED configurations.

**Related files:**  
- `evaluation/gated_tuning_design.md`
- `evaluation/gated_tuning_state.yaml`
- `evaluation/run_gated_tuning_stageA.sbatch`
- `evaluation/run_gated_tuning_stageA_metrics.sbatch`
- `evaluation/run_gated_tuning_stageB.sbatch`
- `evaluation/run_gated_tuning_stageB_metrics.sbatch`
- `evaluation/collect_gated_tuning_stageA.py`
- `evaluation/select_gated_tuning_stageA.py`

---

## 4. GATED 10x PBMC Benchmark

**Results:**  
`evaluation/results_gated/`

**Experiment setup:**  
Runs GATED GLUE on the 10x Multiome PBMC benchmark, including the full reference dataset and subsampled datasets for comparison with the GCN and GAT architectures.

**Related scripts:**  
- `evaluation/run_10x_gated_full_reference.sh`
- `evaluation/run_10x_gated_subsamples.sh`

---

## 5. Learned Gate / Edge Analysis

**Results:**  
`evaluation/gate_analysis/`

**Experiment setup:**  
Analyzes the learned GATED graph edge parameters to investigate whether gate values capture meaningful edge-level structure and how strongly individual guidance-graph edges are retained or suppressed.

**Related scripts:**  
- `evaluation/extract_gated_edge_analysis.py`
- `evaluation/extract_gated_edge_analysis.sbatch`

---

## Storage Policy

Raw experiment directories are intentionally not tracked by Git because they can be several gigabytes in size.

Git should contain:

- experiment scripts
- SLURM submission scripts
- analysis scripts
- experiment configuration/design files
- compact summary tables and figures
- documentation

Large checkpoints, embeddings, intermediate model files, and raw experiment outputs remain on Fir.
