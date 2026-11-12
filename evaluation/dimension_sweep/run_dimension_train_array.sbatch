#!/bin/bash
#SBATCH --job-name=dimA_glue
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=0-11%6
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep/logs/train_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep/logs/train_%A_%a.err
set -euo pipefail

SWEEP=/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep
TASKS=${DIM_TASK_FILE:-$SWEEP/stageA_tasks.csv}
LINE=$(sed -n "$((SLURM_ARRAY_TASK_ID+2))p" "$TASKS")
LINE=${LINE%$'\r'}
IFS=, read -r TASK_ID STAGE ARCH DIM SIZE SUBSEED MODELSEED INPUT_DIR RESULT_DIR <<< "$LINE"
[[ -n "$LINE" ]] || { echo "No task row for array task $SLURM_ARRAY_TASK_ID in $TASKS" >&2; exit 2; }
[[ "$TASK_ID" == "$SLURM_ARRAY_TASK_ID" ]] || { echo "Task ID mismatch: array=$SLURM_ARRAY_TASK_ID csv=$TASK_ID" >&2; exit 2; }
[[ -n "$RESULT_DIR" && "$RESULT_DIR" == /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/results_dimension_sweep/* ]]

case "$ARCH" in
  gcn|gat)
    REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GAT
    RUNNER=$REPO/evaluation/workflow/scripts/run_GLUE.py
    ;;
  gated)
    REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED
    RUNNER=$REPO/evaluation/workflow/scripts/run_GLUE.py
    ;;
  *)
    echo "Unknown architecture: $ARCH" >&2
    exit 2
    ;;
esac
test -s "$RUNNER" || { echo "Runner not found: $RUNNER" >&2; exit 3; }
set +u
eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate /project/6001426/paa40/GlUE_Exp/GLUE/conda
set -u
hash -r
export PYTHONPATH="$REPO"
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

cd "$REPO"
RESOLVED=$(python -c 'import scglue; print(scglue.__file__)')
case "$RESOLVED" in "$REPO"/*) ;; *) echo "wrong scglue import: $RESOLVED" >&2; exit 3;; esac
SIGNATURE=$(python -c 'import inspect, scglue; print(inspect.signature(scglue.models.SCGLUEModel.__init__))')
python -c 'import inspect, scglue, sys; arch=sys.argv[1]; init=inspect.signature(scglue.models.SCGLUEModel.__init__).parameters; compile_=inspect.signature(scglue.models.SCGLUEModel.compile).parameters; required={"graph_encoder"}; required |= {"gat_negative_slope"} if arch == "gat" else set(); required |= {"gate_init"} if arch == "gated" else set(); missing=sorted(required-init.keys()); missing += ["compile.lam_keep"] if arch == "gated" and "lam_keep" not in compile_ else []; missing and sys.exit("Missing SCGLUE API parameters: " + ", ".join(missing))' "$ARCH"
HELP=$(python "$RUNNER" --help)
REQUIRED_FLAGS=(--graph-encoder --dim --alt-dim --lam-graph --lam-align)
if [[ "$ARCH" == gat ]]; then REQUIRED_FLAGS+=(--gat-negative-slope); fi
if [[ "$ARCH" == gated ]]; then REQUIRED_FLAGS+=(--gate-init --lam-keep); fi
for flag in "${REQUIRED_FLAGS[@]}"; do
  grep -q -- "$flag" <<< "$HELP" || { echo "Runner lacks required option: $flag" >&2; exit 3; }
done
printf 'architecture=%s\nrepository=%s\nrunner=%s\nscglue.__file__=%s\nSCGLUEModel.__init__=%s\ndimension=%s\ntask_id=%s\n' \
  "$ARCH" "$REPO" "$RUNNER" "$RESOLVED" "$SIGNATURE" "$DIM" "$TASK_ID"

PRIOR=gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0
RNA="$INPUT_DIR/rna.h5ad"; ATAC="$INPUT_DIR/atac.h5ad"; GRAPH="$INPUT_DIR/$PRIOR/sub.graphml.gz"
for f in "$RNA" "$ATAC" "$GRAPH"; do test -s "$f"; done
if [[ -s "$RESULT_DIR/run_info.yaml" && -s "$RESULT_DIR/final.dill" && -s "$RESULT_DIR/rna_latent.csv" && -s "$RESULT_DIR/atac_latent.csv" && -s "$RESULT_DIR/feature_latent.csv" ]]; then
  echo "Already complete; refusing to overwrite: $RESULT_DIR"; exit 0
fi
mkdir -p "$RESULT_DIR"
TRAIN_LOG="$RESULT_DIR/run_GLUE.log"
if [[ -e "$TRAIN_LOG" ]]; then
  TRAIN_LOG="$RESULT_DIR/run_GLUE.${SLURM_ARRAY_JOB_ID:-manual}_${SLURM_ARRAY_TASK_ID}.log"
  test ! -e "$TRAIN_LOG" || { echo "Refusing to overwrite existing log: $TRAIN_LOG" >&2; exit 4; }
fi

EXTRA=(--graph-encoder "$ARCH")
if [[ "$ARCH" == gat ]]; then EXTRA+=(--gat-negative-slope 0.2); fi
if [[ "$ARCH" == gated ]]; then EXTRA+=(--gate-init 0.95 --lam-keep 0.0); fi
python -u "$RUNNER" --input-rna "$RNA" --input-atac "$ATAC" --prior "$GRAPH" \
 --dim "$DIM" --alt-dim 100 --hidden-depth 2 --hidden-dim 256 --dropout 0.2 \
 --lam-graph 0.02 --lam-align 0.05 --lr 0.002 --neg-samples 10 --data-batch-size 128 \
 "${EXTRA[@]}" --random-seed "$MODELSEED" --train-dir "$RESULT_DIR" --random-sleep --require-converge \
 --output-rna "$RESULT_DIR/rna_latent.csv" --output-atac "$RESULT_DIR/atac_latent.csv" \
 --output-feature "$RESULT_DIR/feature_latent.csv" --run-info "$RESULT_DIR/run_info.yaml" \
 > "$TRAIN_LOG" 2>&1
for f in run_info.yaml final.dill rna_latent.csv atac_latent.csv feature_latent.csv; do test -s "$RESULT_DIR/$f"; done
echo "COMPLETE stage=$STAGE arch=$ARCH dim=$DIM size=$SIZE seed=$SUBSEED import=$RESOLVED"
