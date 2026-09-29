#!/bin/bash
#SBATCH --job-name=dim8000_metrics
#SBATCH --time=04:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --array=0-11%6
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep/logs/metrics_8000_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep/logs/metrics_8000_%A_%a.err
set -euo pipefail
REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED
ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda
TASKS=$REPO/evaluation/dimension_sweep/stageA_8000_tasks.csv
LINE=$(sed -n "$((SLURM_ARRAY_TASK_ID+2))p" "$TASKS")
LINE=${LINE%$'\r'}
IFS=, read -r TASK_ID STAGE ARCH DIM SIZE SUBSEED MODELSEED INPUT_DIR RESULT_DIR <<< "$LINE"
[[ -n "$LINE" ]] || { echo "No task row for array task $SLURM_ARRAY_TASK_ID" >&2; exit 2; }
[[ "$TASK_ID" == "$SLURM_ARRAY_TASK_ID" ]] || { echo "Task ID mismatch: array=$SLURM_ARRAY_TASK_ID csv=$TASK_ID" >&2; exit 2; }
for f in rna_latent.csv atac_latent.csv feature_latent.csv run_info.yaml final.dill; do test -s "$RESULT_DIR/$f"; done
for f in rna_unirep.h5ad atac_unirep.h5ad; do test -s "$INPUT_DIR/$f"; done
METRIC_DIR=$REPO/evaluation/dimension_sweep/metrics_8000_runs/$ARCH/dim_$DIM/seed_$SUBSEED
mkdir -p "$METRIC_DIR"
export PYTHONPATH="$REPO" PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$ENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
cd "$REPO/evaluation"
echo "HOST=$(hostname) TASK=$SLURM_ARRAY_TASK_ID ARCH=$ARCH DIM=$DIM SIZE=$SIZE SUBSEED=$SUBSEED MODELSEED=$MODELSEED"
echo "RESULT_DIR=$RESULT_DIR METRIC_DIR=$METRIC_DIR"
"$ENV/bin/python" -u workflow/scripts/cell_integration.py \
 -d "$INPUT_DIR/rna_unirep.h5ad" "$INPUT_DIR/atac_unirep.h5ad" \
 -l "$RESULT_DIR/rna_latent.csv" "$RESULT_DIR/atac_latent.csv" \
 --cell-type cell_type --domain domain --paired -o "$METRIC_DIR/cell_integration.yaml" \
 > "$METRIC_DIR/cell_integration.log" 2>&1
"$ENV/bin/python" -u workflow/scripts/combine_metrics.py \
 -i "$RESULT_DIR/run_info.yaml" "$METRIC_DIR/cell_integration.yaml" \
 -o "$METRIC_DIR/metrics.yaml" > "$METRIC_DIR/combine_metrics.log" 2>&1
test -s "$METRIC_DIR/metrics.yaml"
echo "COMPLETE arch=$ARCH dim=$DIM size=$SIZE seed=$SUBSEED feature_consistency=DEFERRED"
