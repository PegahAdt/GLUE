#!/bin/bash
#SBATCH --job-name=gate_init_sens
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=0-35%6
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/gate_init_sensitivity/logs/train_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/gate_init_sensitivity/logs/train_%A_%a.err
set -euo pipefail
REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED
ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda
OLD=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation
CFG=$REPO/evaluation/gate_init_sensitivity/training_tasks.csv
line=$(sed -n "$((SLURM_ARRAY_TASK_ID+2))p" "$CFG"); IFS=, read -r task gate size seed model_seed run <<< "$line"
[[ "$task" == "$SLURM_ARRAY_TASK_ID" ]] || exit 2
input=$OLD/results_gcn_h100/raw/10x-Multiome-Pbmc10k/subsample_size:${size}-subsample_seed:${seed}
prior=$input/gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/sub.graphml.gz
mkdir -p "$run"
export PYTHONPATH="$REPO" PYTHONNOUSERSITE=1 LD_LIBRARY_PATH="$ENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
resolved=$($ENV/bin/python -c 'import pathlib,scglue; print(pathlib.Path(scglue.__file__).resolve())')
[[ "$resolved" == "$REPO"/scglue/* ]] || { echo "Wrong scglue: $resolved" >&2; exit 3; }
$ENV/bin/python -u "$REPO/evaluation/validate_10x_gated_subsamples.py" --size "$size" --seed "$seed"
cd "$REPO/evaluation"
$ENV/bin/python -u workflow/scripts/run_GLUE.py --input-rna "$input/rna.h5ad" --input-atac "$input/atac.h5ad" --prior "$prior" \
 --dim 50 --alt-dim 100 --hidden-depth 2 --hidden-dim 256 --dropout 0.2 --lam-graph 0.02 --lam-align 0.05 \
 --lr 0.002 --neg-samples 10 --data-batch-size 128 --graph-encoder gated --gate-init "$gate" --lam-keep 0.0 \
 --random-seed "$model_seed" --train-dir "$run" --random-sleep --require-converge --output-rna "$run/rna_latent.csv" \
 --output-atac "$run/atac_latent.csv" --output-feature "$run/feature_latent.csv" --run-info "$run/run_info.yaml" > "$run/run_GLUE.log" 2>&1
for f in rna_latent.csv atac_latent.csv feature_latent.csv run_info.yaml final.dill gate_diagnostics.yaml; do test -s "$run/$f"; done
echo "COMPLETE gate=$gate size=$size seed=$seed model_seed=$model_seed scglue=$resolved"
