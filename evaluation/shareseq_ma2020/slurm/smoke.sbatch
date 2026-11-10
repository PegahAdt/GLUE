#!/bin/bash
#SBATCH --job-name=share_smoke
#SBATCH --time=02:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/smoke_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/smoke_%j.err
set -euo pipefail
ROOT=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020; ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda; IMPL=/project/6001426/paa40/GlUE_Exp/GLUE_GATED; OUT=$ROOT/results/smoke_gated_500
set +u
eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate "$ENV"
set -u
hash -r
mkdir -p "$OUT"
if [[ -s "$OUT/final.dill" ]]; then
  exec bash "$ROOT/slurm/rescue_smoke.sbatch"
fi
head -500 "$ROOT/manifests/cells_size8000_seed0.txt" > "$ROOT/manifests/cells_smoke500_seed0.txt"
$ENV/bin/python "$ROOT/scripts/materialize_run_inputs.py" "$OUT" "$ROOT/data/rna_prepared.h5ad" "$ROOT/data/atac_prepared.h5ad" "$ROOT/manifests/cells_smoke500_seed0.txt"
export PYTHONPATH=$IMPL PYTHONNOUSERSITE=1 LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
$ENV/bin/python -u "$IMPL/evaluation/workflow/scripts/run_GLUE.py" --input-rna "$OUT/rna.h5ad" --input-atac "$OUT/atac.h5ad" --prior "$ROOT/data/guidance.graphml.gz" --dim 50 --alt-dim 100 --hidden-depth 2 --hidden-dim 256 --dropout .2 --lam-graph .02 --lam-align .05 --lr .002 --neg-samples 10 --data-batch-size 128 --random-seed 0 --train-dir "$OUT" --graph-encoder gated --gate-init .95 --lam-keep 0 --require-converge --output-rna "$OUT/rna_latent.csv" --output-atac "$OUT/atac_latent.csv" --output-feature "$OUT/feature_latent.csv" --run-info "$OUT/run_info.yaml" > "$OUT/run_GLUE.log" 2>&1
for f in final.dill rna_latent.csv atac_latent.csv feature_latent.csv run_info.yaml gate_diagnostics.yaml; do test -s "$OUT/$f"; done
exec bash "$ROOT/slurm/rescue_smoke.sbatch"
