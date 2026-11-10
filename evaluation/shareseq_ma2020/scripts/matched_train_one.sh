#!/bin/bash
set -euo pipefail
ROOT=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020
REPO=/project/6001426/paa40/GlUE_Exp/GLUE
ENV=$REPO/conda
# Match submit_all.sh / successful full-data task 58723587_1.
# python -c prepends cwd before PYTHONPATH; never probe from baseline root.
cd "$ROOT"
set +u
eval "$(/home/paa40/bin/micromamba shell hook --shell bash)"
micromamba activate "$ENV"
set -u
hash -r
ROW=${1:?manifest row required}
eval "$($ENV/bin/python "$ROOT/scripts/matched_read_manifest.py" "$ROW" shell)"
mkdir -p "$output_directory"
if "$ENV/bin/python" "$ROOT/scripts/matched_validate_run.py" "$ROW" --quiet; then echo "REUSE $run_id"; exit 0; fi
"$ENV/bin/python" "$ROOT/scripts/materialize_run_inputs.py" "$output_directory" "$rna_path" "$atac_path" "$cell_manifest_path"
"$ENV/bin/python" "$ROOT/scripts/matched_check_inputs.py" "$ROW"
case "$architecture" in
  gcn) IMPL=$REPO; EXTRA=() ;;
  gat) IMPL=/project/6001426/paa40/GlUE_Exp/GLUE_GAT; EXTRA=(--graph-encoder gat --gat-negative-slope "$gat_negative_slope") ;;
  gated) IMPL=/project/6001426/paa40/GlUE_Exp/GLUE_GATED; EXTRA=(--graph-encoder gated --gate-init "$gate_init" --lam-keep "$lam_keep") ;;
  *) echo "Unknown architecture $architecture" >&2; exit 2;;
esac
export PYTHONPATH=$IMPL PYTHONNOUSERSITE=1 LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8} MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
resolved=$($ENV/bin/python -c 'import pathlib,scglue; print(pathlib.Path(scglue.__file__).resolve())')
echo "scglue.__file__=$resolved"
expected=$($ENV/bin/python -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$IMPL/scglue/__init__.py")
[[ "$resolved" == "$expected" ]] || { echo "Wrong scglue: $resolved" >&2; exit 3; }
args=(--input-rna "$output_directory/rna.h5ad" --input-atac "$output_directory/atac.h5ad" --prior "$graph_path" --dim 50 --alt-dim 100 --hidden-depth 2 --hidden-dim 256 --dropout 0.2 --lam-graph 0.02 --lam-align 0.05 --lr 0.002 --neg-samples 10 --data-batch-size 128 --random-seed "$model_seed" --train-dir "$output_directory" --require-converge --output-rna "$output_directory/rna_latent.csv" --output-atac "$output_directory/atac_latent.csv" --output-feature "$output_directory/feature_latent.csv" --run-info "$output_directory/run_info.yaml")
$ENV/bin/python -u "$IMPL/evaluation/workflow/scripts/run_GLUE.py" "${args[@]}" "${EXTRA[@]}" > "$output_directory/run_GLUE.log" 2>&1
$ENV/bin/python "$ROOT/scripts/matched_stamp_run.py" "$ROW"
$ENV/bin/python "$ROOT/scripts/matched_validate_run.py" "$ROW"
