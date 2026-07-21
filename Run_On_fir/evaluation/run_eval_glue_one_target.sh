#!/bin/bash
#SBATCH --job-name=eval_glue_one
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/eval_glue_one_%j.out
#SBATCH --error=logs/eval_glue_one_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
source /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/activate_glue.sh

cd /project/6001426/paa40/GlUE_Exp/GLUE/evaluation
cp /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/evaluation/glue_official_targets.txt glue_official_targets.txt 2>/dev/null || true
cp /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/evaluation/glue_targets_250_500.txt glue_targets_250_500.txt 2>/dev/null || true

snakemake \
  -s workflow/Snakefile \
  --configfile config/config.yaml \
  -j1 -pr \
  "results/raw/10x-Multiome-Pbmc10k/subsample_size:250-subsample_seed:1/gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/GLUE/dim:50-alt_dim:100-hidden_depth:2-hidden_dim:256-dropout:0.2-lam_graph:0.02-lam_align:0.05-neg_samples:10/seed:0/metrics.yaml"
