#!/bin/bash

set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL="$REPO/evaluation"

cd "$REPO"

CURRENT_BRANCH=$(git branch --show-current)

if [[ "$CURRENT_BRANCH" != "GAT_GLUE" ]]; then
    echo "ERROR: Expected branch GAT_GLUE, found: $CURRENT_BRANCH"
    exit 1
fi

if [[ ! -d "$EVAL/workflow_gat_10x" ]]; then
    echo "ERROR: Missing working GAT workflow:"
    echo "$EVAL/workflow_gat_10x"
    exit 1
fi

if [[ ! -f "$EVAL/gat_10x_subsample_targets.txt" ]]; then
    echo "ERROR: Missing GAT target list."
    exit 1
fi

if [[ ! -f "$EVAL/gat_10x_reference_target.txt" ]]; then
    echo "ERROR: Missing GAT reference target."
    exit 1
fi

if [[ ! -f "$EVAL/run_10x_gat_reference.sh" ]]; then
    echo "ERROR: Missing GAT reference job script."
    exit 1
fi

if [[ ! -f "$EVAL/run_10x_gat_subsamples.sh" ]]; then
    echo "ERROR: Missing GAT subsample job script."
    exit 1
fi

cd "$EVAL"

echo "Creating GCN target lists..."

sed \
    's#results_gat/raw#results_gcn_h100/raw#g' \
    gat_10x_subsample_targets.txt \
    > gcn_h100_10x_subsample_targets.txt

sed \
    's#results_gat/raw#results_gcn_h100/raw#g' \
    gat_10x_reference_target.txt \
    > gcn_h100_10x_reference_target.txt

GCN_TARGET_COUNT=$(
    wc -l < gcn_h100_10x_subsample_targets.txt
)

if [[ "$GCN_TARGET_COUNT" -ne 48 ]]; then
    echo "ERROR: Expected 48 GCN targets, found $GCN_TARGET_COUNT"
    exit 1
fi

echo "Creating isolated GCN workflow..."

rm -rf workflow_gcn_10x
cp -a workflow_gat_10x workflow_gcn_10x

# Redirect GCN output away from both old GCN results and new GAT results.
while IFS= read -r FILE; do
    [[ -n "$FILE" ]] || continue

    sed -i \
        's#results_gat/raw#results_gcn_h100/raw#g' \
        "$FILE"
done < <(
    grep -RIl \
        'results_gat/raw' \
        workflow_gcn_10x \
        || true
)

# Select the original GCN graph encoder.
while IFS= read -r FILE; do
    [[ -n "$FILE" ]] || continue

    sed -i \
        's#--graph-encoder gat#--graph-encoder gcn#g' \
        "$FILE"
done < <(
    grep -RIl \
        -- '--graph-encoder gat' \
        workflow_gcn_10x \
        || true
)

# GAT negative slope has no meaning for GCN, so remove the option.
while IFS= read -r FILE; do
    [[ -n "$FILE" ]] || continue

    sed -i \
        '/--gat-negative-slope 0\.2/d' \
        "$FILE"
done < <(
    grep -RIl \
        -- '--gat-negative-slope 0.2' \
        workflow_gcn_10x \
        || true
)

echo "Creating GCN Slurm scripts..."

cp \
    run_10x_gat_reference.sh \
    run_10x_gcn_reference.sh

cp \
    run_10x_gat_subsamples.sh \
    run_10x_gcn_subsamples.sh

sed -i \
    -e 's/gat10x_ref/gcn10x_ref/g' \
    -e 's/workflow_gat_10x/workflow_gcn_10x/g' \
    -e 's/gat_10x_reference_target/gcn_h100_10x_reference_target/g' \
    -e 's/results_gat/results_gcn_h100/g' \
    run_10x_gcn_reference.sh

sed -i \
    -e 's/gat10x_sub/gcn10x_sub/g' \
    -e 's/workflow_gat_10x/workflow_gcn_10x/g' \
    -e 's/gat_10x_subsample_targets/gcn_h100_10x_subsample_targets/g' \
    -e 's/results_gat/results_gcn_h100/g' \
    run_10x_gcn_subsamples.sh

chmod +x \
    run_10x_gcn_reference.sh \
    run_10x_gcn_subsamples.sh

echo
echo "Checking Slurm scripts..."

bash -n run_10x_gcn_reference.sh
bash -n run_10x_gcn_subsamples.sh

grep -nE \
    '#SBATCH --job-name|#SBATCH --array|#SBATCH --gpus-per-node|workflow_gcn|gcn_h100' \
    run_10x_gcn_reference.sh \
    run_10x_gcn_subsamples.sh

echo
echo "Activating GLUE environment..."

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u

micromamba activate "$REPO/conda"
hash -r

unset PYTHONPATH || true
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo
echo "Running GCN dry run..."

FIRST_TARGET=$(
    head -n 1 gcn_h100_10x_subsample_targets.txt
)

DRY_RUN_LOG="results_gcn_h100/gcn_10x_dry_run.txt"

mkdir -p results_gcn_h100

snakemake \
    --snakefile workflow_gcn_10x/Snakefile \
    --cores 1 \
    --dry-run \
    --printshellcmds \
    "$FIRST_TARGET" \
    | tee "$DRY_RUN_LOG"

if ! grep -q \
    -- '--graph-encoder gcn' \
    "$DRY_RUN_LOG"; then
    echo
    echo "ERROR: Dry run did not contain --graph-encoder gcn"
    exit 1
fi

if grep -q \
    -- '--graph-encoder gat' \
    "$DRY_RUN_LOG"; then
    echo
    echo "ERROR: Dry run still contains --graph-encoder gat"
    exit 1
fi

echo
echo "GCN setup and dry run succeeded."
echo "Targets: $GCN_TARGET_COUNT"
echo "Output root: results_gcn_h100/raw"
