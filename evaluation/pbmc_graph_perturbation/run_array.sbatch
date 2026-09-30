#!/bin/bash
#SBATCH --job-name=pbmc_graph_gated
#SBATCH --time=06:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=0-17%3
#SBATCH --chdir=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_perturbation/logs/train_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_perturbation/logs/train_%A_%a.err

set -euo pipefail

REPO=/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC
REQUIRED_BRANCH=GATED_PBMC_GRAPH_EXPERIMENTS
EXPERIMENT="$REPO/evaluation/pbmc_graph_perturbation"
MANIFEST=${PBMC_GRAPH_MANIFEST:-"$EXPERIMENT/manifest.csv"}
GLUE_ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda
DATASET=10x-Multiome-Pbmc10k
INPUT_DIR="/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/results_gcn_h100/raw/$DATASET/original"
RNA="$INPUT_DIR/rna.h5ad"
ATAC="$INPUT_DIR/atac.h5ad"
GRAPH="$INPUT_DIR/gene_region:combined-extend_range:0-corrupt_rate:0.0-corrupt_seed:0/sub.graphml.gz"
RUNNER="$REPO/evaluation/workflow/scripts/run_GLUE.py"
EXPECTED_CONDITIONS=(original retain_75 retain_50 retain_25 retain_10 randomized)
EXPECTED_FRACTIONS=("" 0.75 0.50 0.25 0.10 "")
DRY_RUN=${DRY_RUN:-0}

die() {
    echo "ERROR: $*" >&2
    exit 2
}

[[ "$DRY_RUN" == 0 || "$DRY_RUN" == 1 ]] || die "DRY_RUN must be 0 or 1"
[[ "$(git -C "$REPO" branch --show-current)" == "$REQUIRED_BRANCH" ]] ||
    die "Expected branch $REQUIRED_BRANCH in $REPO"
for file in "$RNA" "$ATAC" "$GRAPH" "$RUNNER" \
    "$REPO/evaluation/workflow/scripts/graph_perturbation.py" "$MANIFEST"; do
    [[ -s "$file" ]] || die "Missing or empty file: $file"
done
[[ -x "$GLUE_ENV/bin/python" ]] || die "Missing Python: $GLUE_ENV/bin/python"

# CSV values are deliberately unquoted and contain no commas. Empty cells
# denote inactive parameters, which must not be passed to run_GLUE.py.
mapfile -t MANIFEST_ROWS < "$MANIFEST"
[[ ${#MANIFEST_ROWS[@]} == 19 ]] || die "Manifest must contain one header and 18 runs"
[[ "${MANIFEST_ROWS[0]%$'\r'}" == \
    task_id,condition,graph_perturbation,retain_fraction,swap_multiplier,graph_seed,model_seed,run_dir ]] ||
    die "Unexpected manifest header"

load_task() {
    local index="$1" line extra expected_condition expected_fraction expected_mode expected_swap
    line="${MANIFEST_ROWS[$((index + 1))]%$'\r'}"
    IFS=, read -r TASK_ID CONDITION GRAPH_PERTURBATION RETAIN_FRACTION \
        SWAP_MULTIPLIER GRAPH_SEED MODEL_SEED RUN_DIR extra <<< "$line"
    expected_condition="${EXPECTED_CONDITIONS[$((index / 3))]}"
    expected_fraction="${EXPECTED_FRACTIONS[$((index / 3))]}"
    expected_mode=subsample
    expected_swap=""
    case "$expected_condition" in
        original) expected_mode=none ;;
        randomized) expected_mode=randomize; expected_swap=10.0 ;;
    esac
    [[ "$TASK_ID" == "$index" && -z "$extra" ]] || die "Invalid task ID/columns at row $index"
    [[ "$CONDITION" == "$expected_condition" ]] || die "Wrong condition at task $index"
    [[ "$GRAPH_PERTURBATION" == "$expected_mode" ]] || die "Wrong perturbation at task $index"
    [[ "$RETAIN_FRACTION" == "$expected_fraction" ]] || die "Wrong retain fraction at task $index"
    [[ "$SWAP_MULTIPLIER" == "$expected_swap" ]] || die "Wrong swap multiplier at task $index"
    [[ "$GRAPH_SEED" == 0 && "$MODEL_SEED" == "$((index % 3))" ]] || die "Wrong seeds at task $index"
    [[ "$RUN_DIR" == "$EXPERIMENT/results/$DATASET/$CONDITION/graph_seed:0/model_seed:$MODEL_SEED" ]] ||
        die "Unexpected result directory at task $index: $RUN_DIR"
}

# Validate the entire experiment before selecting or launching any one task.
for index in {0..17}; do
    load_task "$index"
done

build_command() {
    COMMAND=(
        "$GLUE_ENV/bin/python" -u "$RUNNER"
        --input-rna "$RNA" --input-atac "$ATAC" --prior "$GRAPH"
        --dim 50 --alt-dim 100 --hidden-depth 2 --hidden-dim 256 --dropout 0.2
        --lam-graph 0.02 --lam-align 0.05 --lr 0.002 --neg-samples 10
        --data-batch-size 128 --graph-encoder gated --gate-init 0.95 --lam-keep 0.0
        --graph-perturbation "$GRAPH_PERTURBATION" --graph-seed "$GRAPH_SEED"
    )
    case "$GRAPH_PERTURBATION" in
        subsample) COMMAND+=(--graph-retain-fraction "$RETAIN_FRACTION") ;;
        randomize) COMMAND+=(--graph-swap-multiplier "$SWAP_MULTIPLIER") ;;
    esac
    COMMAND+=(
        --random-seed "$MODEL_SEED" --train-dir "$RUN_DIR" --random-sleep --require-converge
        --output-rna "$RUN_DIR/rna_latent.csv" --output-atac "$RUN_DIR/atac_latent.csv"
        --output-feature "$RUN_DIR/feature_latent.csv" --run-info "$RUN_DIR/run_info.yaml"
    )
}

print_command() {
    printf 'task_id=%s condition=%s graph_seed=%s model_seed=%s\n' \
        "$TASK_ID" "$CONDITION" "$GRAPH_SEED" "$MODEL_SEED"
    printf '%q ' "${COMMAND[@]}"
    printf '> %q 2>&1\n' "$RUN_DIR/run_GLUE.log"
}

if [[ "$DRY_RUN" == 1 ]]; then
    [[ $# -le 1 ]] || die "Usage: DRY_RUN=1 bash run_array.sbatch [all|task_id]"
    selection=${1:-all}
    if [[ "$selection" == all ]]; then
        for index in {0..17}; do
            load_task "$index"
            build_command
            print_command
        done
    else
        [[ "$selection" =~ ^([0-9]|1[0-7])$ ]] || die "Task ID must be 0-17"
        load_task "$selection"
        build_command
        print_command
    fi
    # No environment activation, output creation, Python execution or submission.
    exit 0
fi

[[ $# == 0 ]] || die "Positional task selection is only allowed in DRY_RUN mode"
[[ -n "${SLURM_JOB_ID:-}" && "${SLURM_ARRAY_TASK_ID:-}" =~ ^([0-9]|1[0-7])$ ]] ||
    die "Training requires a Slurm array task; use DRY_RUN=1 for inspection"
load_task "$SLURM_ARRAY_TASK_ID"
build_command
cd "$REPO"

# An exclusive mkdir prevents accidental overwrites and duplicate task launches.
mkdir -p "$(dirname "$RUN_DIR")"
mkdir "$RUN_DIR" || die "Run directory already exists; refusing to overwrite: $RUN_DIR"
cp "$MANIFEST" "$RUN_DIR/manifest.csv"

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
micromamba activate "$GLUE_ENV"
set -u
hash -r
export PYTHONPATH="$REPO"
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$GLUE_ENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMBA_CACHE_DIR="${SLURM_TMPDIR:-$RUN_DIR}/numba_cache"
export MPLCONFIGDIR="${SLURM_TMPDIR:-$RUN_DIR}/matplotlib"

printf 'repository=%s branch=%s commit=%s manifest=%s\n' \
    "$REPO" "$REQUIRED_BRANCH" "$(git -C "$REPO" rev-parse HEAD)" "$MANIFEST"
print_command
"${COMMAND[@]}" > "$RUN_DIR/run_GLUE.log" 2>&1

for file in rna_latent.csv atac_latent.csv feature_latent.csv run_info.yaml \
    gate_diagnostics.yaml final.dill; do
    [[ -s "$RUN_DIR/$file" && ! -L "$RUN_DIR/$file" ]] || die "Missing run output: $RUN_DIR/$file"
done
echo "COMPLETE task_id=$TASK_ID condition=$CONDITION graph_seed=$GRAPH_SEED model_seed=$MODEL_SEED"
