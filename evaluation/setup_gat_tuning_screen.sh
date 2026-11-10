#!/usr/bin/env bash
set -euo pipefail


# ============================================================
# Locations
# ============================================================

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL_DIR="$REPO/evaluation"

TEMPLATE_WORKFLOW="$EVAL_DIR/workflow_gat_10x"
BASE_SUBSAMPLE_TARGETS="$EVAL_DIR/gat_10x_subsample_targets.txt"
BASE_REFERENCE_TARGET="$EVAL_DIR/gat_10x_reference_target.txt"

BATCH_NAME="${1:-screen_$(date +%Y%m%d_%H%M%S)}"

BATCH_DIR="$EVAL_DIR/gat_tuning_10x/$BATCH_NAME"
RESULT_BATCH_ROOT="$EVAL_DIR/results_gat_tuning/$BATCH_NAME"


# ============================================================
# Safety checks
# ============================================================

for required_path in \
    "$TEMPLATE_WORKFLOW" \
    "$BASE_SUBSAMPLE_TARGETS" \
    "$BASE_REFERENCE_TARGET"
do
    if [[ ! -e "$required_path" ]]; then
        echo "ERROR: Required path does not exist:"
        echo "  $required_path"
        exit 1
    fi
done

CURRENT_BRANCH=$(git -C "$REPO" branch --show-current)
CURRENT_COMMIT=$(git -C "$REPO" rev-parse HEAD)

if [[ "$CURRENT_BRANCH" != "GAT_GLUE" ]]; then
    echo "ERROR: The original repository must be on GAT_GLUE."
    echo "Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Never reuse an existing batch directory.
if [[ -e "$BATCH_DIR" ]]; then
    echo "ERROR: Batch already exists:"
    echo "  $BATCH_DIR"
    echo
    echo "Choose a new batch name, such as screen_v2."
    exit 1
fi

if [[ -e "$RESULT_BATCH_ROOT" ]]; then
    echo "ERROR: Result batch already exists:"
    echo "  $RESULT_BATCH_ROOT"
    exit 1
fi

mkdir -p \
    "$BATCH_DIR/configs" \
    "$BATCH_DIR/logs" \
    "$RESULT_BATCH_ROOT"

printf '%s\n' "$CURRENT_COMMIT" \
    > "$BATCH_DIR/base_commit.txt"

printf '%s\n' "$CURRENT_BRANCH" \
    > "$BATCH_DIR/base_branch.txt"


# ============================================================
# Parameter configurations
#
# Every row changes one value relative to:
#
# lr                 = 0.002
# lam_graph          = 0.02
# lam_align          = 0.05
# gat_negative_slope = 0.2
# ============================================================

cat > "$BATCH_DIR/configs.tsv" <<'EOF'
config_name	lr	lam_graph	lam_align	gat_negative_slope
lr_0p001	0.001	0.02	0.05	0.2
lr_0p0005	0.0005	0.02	0.05	0.2
align_0p03	0.002	0.02	0.03	0.2
align_0p08	0.002	0.02	0.08	0.2
align_0p10	0.002	0.02	0.10	0.2
graph_0p01	0.002	0.01	0.05	0.2
graph_0p05	0.002	0.05	0.05	0.2
slope_0p05	0.002	0.02	0.05	0.05
slope_0p10	0.002	0.02	0.05	0.10
slope_0p40	0.002	0.02	0.05	0.40
EOF


# ============================================================
# Generate isolated workflows and target lists
# ============================================================

python - \
    "$BATCH_DIR" \
    "$RESULT_BATCH_ROOT" \
    "$TEMPLATE_WORKFLOW" \
    "$BASE_SUBSAMPLE_TARGETS" \
    "$BASE_REFERENCE_TARGET" <<'PY'
from __future__ import annotations

import csv
import re
import shutil
import sys
from pathlib import Path


batch_dir = Path(sys.argv[1]).resolve()
result_batch_root = Path(sys.argv[2]).resolve()
template_workflow = Path(sys.argv[3]).resolve()
base_subsample_file = Path(sys.argv[4]).resolve()
base_reference_file = Path(sys.argv[5]).resolve()

config_table = batch_dir / "configs.tsv"

selected_sizes = {250, 2000, 8000}
selected_seeds = {0, 1, 2}


def read_nonempty_lines(path: Path):
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip()
    ]


base_subsample_targets = read_nonempty_lines(
    base_subsample_file
)

base_reference_targets = read_nonempty_lines(
    base_reference_file
)

if len(base_reference_targets) != 1:
    raise RuntimeError(
        "Expected exactly one GAT reference target, "
        f"but found {len(base_reference_targets)}."
    )


def parse_subsample(target: str):
    size_match = re.search(
        r"subsample_size:(\d+)",
        target
    )

    seed_match = re.search(
        r"subsample_seed:(\d+)",
        target
    )

    if size_match is None or seed_match is None:
        return None

    return (
        int(size_match.group(1)),
        int(seed_match.group(1)),
    )


selected_base_targets = []

for target in base_subsample_targets:
    parsed = parse_subsample(target)

    if parsed is None:
        continue

    size, seed = parsed

    if (
        size in selected_sizes
        and seed in selected_seeds
    ):
        selected_base_targets.append(target)

selected_base_targets.sort(
    key=lambda target: (
        parse_subsample(target)[0],
        parse_subsample(target)[1],
    )
)

if len(selected_base_targets) != 9:
    raise RuntimeError(
        "Expected 9 selected subsample targets "
        "(3 sizes x 3 seeds), but found "
        f"{len(selected_base_targets)}."
    )


def reroot_target(
    target: str,
    result_root: Path,
    lam_graph: str,
    lam_align: str,
) -> str:
    marker = "results_gat/raw/"

    marker_index = target.find(marker)

    if marker_index < 0:
        raise RuntimeError(
            "Could not find the original GAT result root in:\n"
            f"{target}"
        )

    suffix = target[
        marker_index + len(marker):
    ]

    updated = (
        result_root.as_posix().rstrip("/")
        + "/"
        + suffix
    )

    updated = re.sub(
        r"lam_graph:[^/]+",
        f"lam_graph:{lam_graph}",
        updated,
        count=1,
    )

    updated = re.sub(
        r"lam_align:[^/]+",
        f"lam_align:{lam_align}",
        updated,
        count=1,
    )

    return updated


def patch_workflow_text(
    workflow_dir: Path,
    old_result_root: str,
    new_result_root: str,
) -> None:
    for path in workflow_dir.rglob("*"):
        if not path.is_file():
            continue

        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue

        if old_result_root in text:
            path.write_text(
                text.replace(
                    old_result_root,
                    new_result_root,
                )
            )


def patch_methods(
    methods_path: Path,
    learning_rate: str,
    negative_slope: str,
) -> None:
    text = methods_path.read_text()

    if "--graph-encoder gat" not in text:
        raise RuntimeError(
            "The template workflow does not contain "
            "`--graph-encoder gat`."
        )

    text, slope_count = re.subn(
        r"--gat-negative-slope\s+[^\s\"]+",
        f"--gat-negative-slope {negative_slope}",
        text,
    )

    if slope_count != 1:
        raise RuntimeError(
            "Expected exactly one GAT negative-slope flag, "
            f"but replaced {slope_count}."
        )

    lr_pattern = r"--lr\s+[^\s\"]+"

    if re.search(lr_pattern, text):
        text, lr_count = re.subn(
            lr_pattern,
            f"--lr {learning_rate}",
            text,
        )

        if lr_count != 1:
            raise RuntimeError(
                "Expected exactly one learning-rate flag, "
                f"but replaced {lr_count}."
            )
    else:
        needle = (
            '"--lam-graph '
            '{wildcards.lam_graph} "'
        )

        if needle not in text:
            raise RuntimeError(
                "Could not locate the lam_graph command "
                "in methods.smk."
            )

        replacement = (
            f'"--lr {learning_rate} "\n'
            f'        {needle}'
        )

        text = text.replace(
            needle,
            replacement,
            1,
        )

    methods_path.write_text(text)

    final_text = methods_path.read_text()

    required_fragments = [
        "--graph-encoder gat",
        f"--gat-negative-slope {negative_slope}",
        f"--lr {learning_rate}",
    ]

    for fragment in required_fragments:
        if fragment not in final_text:
            raise RuntimeError(
                f"Missing required command fragment: {fragment}"
            )


manifest_rows = []

with config_table.open(newline="") as handle:
    reader = csv.DictReader(
        handle,
        delimiter="\t",
    )

    for row in reader:
        name = row["config_name"]
        learning_rate = row["lr"]
        lam_graph = row["lam_graph"]
        lam_align = row["lam_align"]
        negative_slope = row[
            "gat_negative_slope"
        ]

        config_dir = (
            batch_dir
            / "configs"
            / name
        )

        workflow_dir = (
            config_dir
            / "workflow"
        )

        result_root = (
            result_batch_root
            / name
            / "raw"
        ).resolve()

        config_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        result_root.mkdir(
            parents=True,
            exist_ok=False,
        )

        shutil.copytree(
            template_workflow,
            workflow_dir,
        )

        # Replace hard-coded results_gat/raw references with
        # this configuration's isolated result directory.
        patch_workflow_text(
            workflow_dir,
            "results_gat/raw",
            result_root.as_posix(),
        )

        methods_path = (
            workflow_dir
            / "rules"
            / "methods.smk"
        )

        patch_methods(
            methods_path,
            learning_rate,
            negative_slope,
        )

        reference_target = reroot_target(
            base_reference_targets[0],
            result_root,
            lam_graph,
            lam_align,
        )

        subsample_targets = [
            reroot_target(
                target,
                result_root,
                lam_graph,
                lam_align,
            )
            for target in selected_base_targets
        ]

        target_file = (
            config_dir
            / "targets.txt"
        )

        target_file.write_text(
            "\n".join(
                [reference_target]
                + subsample_targets
            )
            + "\n"
        )

        parameter_file = (
            config_dir
            / "parameters.tsv"
        )

        parameter_file.write_text(
            "parameter\tvalue\n"
            f"lr\t{learning_rate}\n"
            f"lam_graph\t{lam_graph}\n"
            f"lam_align\t{lam_align}\n"
            f"gat_negative_slope\t{negative_slope}\n"
        )

        manifest_rows.append({
            "config_name": name,
            "lr": learning_rate,
            "lam_graph": lam_graph,
            "lam_align": lam_align,
            "gat_negative_slope": negative_slope,
            "result_root": result_root.as_posix(),
            "workflow": workflow_dir.as_posix(),
            "target_file": target_file.as_posix(),
            "target_count": 1 + len(subsample_targets),
        })


manifest_path = batch_dir / "manifest.tsv"

with manifest_path.open(
    "w",
    newline="",
) as handle:
    fieldnames = list(
        manifest_rows[0].keys()
    )

    writer = csv.DictWriter(
        handle,
        fieldnames=fieldnames,
        delimiter="\t",
    )

    writer.writeheader()
    writer.writerows(manifest_rows)


print("Generated configurations:")

for row in manifest_rows:
    print(
        f"  {row['config_name']}: "
        f"{row['target_count']} targets -> "
        f"{row['result_root']}"
    )
PY


# ============================================================
# Create the Slurm array worker
#
# Each array task handles one configuration:
#
#   1 full-data reference
#   9 subsample metric targets
#
# GPU tasks are run one at a time within the configuration
# because the Slurm allocation contains one GPU.
# ============================================================

cat > "$BATCH_DIR/run_one_config.sbatch" <<'SBATCH'
#!/usr/bin/env bash
#SBATCH --job-name=gat10x_tune
#SBATCH --time=2-00:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=192G
#SBATCH --gpus-per-node=h100:1

set -euo pipefail

BATCH_DIR="${1:?Batch directory argument is required}"

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL_DIR="$REPO/evaluation"

CONFIG_TABLE="$BATCH_DIR/configs.tsv"
EXPECTED_COMMIT=$(cat "$BATCH_DIR/base_commit.txt")

CURRENT_COMMIT=$(git -C "$REPO" rev-parse HEAD)

if [[ "$CURRENT_COMMIT" != "$EXPECTED_COMMIT" ]]; then
    echo "ERROR: Repository commit changed after setup."
    echo "Expected: $EXPECTED_COMMIT"
    echo "Current:  $CURRENT_COMMIT"
    echo
    echo "This job is stopping to avoid running a different model."
    exit 1
fi

LINE_NUMBER=$((SLURM_ARRAY_TASK_ID + 2))

CONFIG_LINE=$(
    awk -F $'\t' \
        -v line_number="$LINE_NUMBER" \
        'NR == line_number { print; exit }' \
        "$CONFIG_TABLE"
)

if [[ -z "$CONFIG_LINE" ]]; then
    echo "ERROR: No configuration for array index:"
    echo "  $SLURM_ARRAY_TASK_ID"
    exit 1
fi

IFS=$'\t' read -r \
    CONFIG_NAME \
    LEARNING_RATE \
    LAM_GRAPH \
    LAM_ALIGN \
    NEGATIVE_SLOPE \
    <<< "$CONFIG_LINE"

CONFIG_DIR="$BATCH_DIR/configs/$CONFIG_NAME"
WORKFLOW="$CONFIG_DIR/workflow/Snakefile"
TARGET_FILE="$CONFIG_DIR/targets.txt"

if [[ ! -s "$TARGET_FILE" ]]; then
    echo "ERROR: Missing target file:"
    echo "  $TARGET_FILE"
    exit 1
fi

mapfile -t TARGETS < "$TARGET_FILE"

if [[ "${#TARGETS[@]}" -ne 10 ]]; then
    echo "ERROR: Expected 10 targets but found:"
    echo "  ${#TARGETS[@]}"
    exit 1
fi

echo "============================================================"
echo "GAT tuning configuration"
echo "============================================================"
echo "Slurm job:         ${SLURM_JOB_ID}"
echo "Array index:       ${SLURM_ARRAY_TASK_ID}"
echo "Configuration:     ${CONFIG_NAME}"
echo "Learning rate:     ${LEARNING_RATE}"
echo "lam_graph:         ${LAM_GRAPH}"
echo "lam_align:         ${LAM_ALIGN}"
echo "Negative slope:    ${NEGATIVE_SLOPE}"
echo "Repository commit: ${CURRENT_COMMIT}"
echo "Targets:           ${#TARGETS[@]}"
echo "Started:           $(date)"
echo "============================================================"

cat > "$CONFIG_DIR/job_${SLURM_JOB_ID}.txt" <<EOF
job_id=${SLURM_JOB_ID}
array_task_id=${SLURM_ARRAY_TASK_ID}
config_name=${CONFIG_NAME}
lr=${LEARNING_RATE}
lam_graph=${LAM_GRAPH}
lam_align=${LAM_ALIGN}
gat_negative_slope=${NEGATIVE_SLOPE}
commit=${CURRENT_COMMIT}
started=$(date)
EOF


# Activate the exact GLUE environment.
set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u

micromamba activate "$REPO/conda"
hash -r

unset PYTHONHOME || true
export PYTHONNOUSERSITE=1
export PYTHONPATH="$REPO"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo
echo "Python:"
which python

echo
echo "Snakemake:"
which snakemake

echo
echo "Imported scglue:"
python - <<'PY'
import scglue
print(scglue.__file__)
PY


# All configurations have isolated output roots, so separate
# Snakemake processes cannot overwrite one another.
cd "$EVAL_DIR"

snakemake \
    --snakefile "$WORKFLOW" \
    --cores "$SLURM_CPUS_PER_TASK" \
    --resources gpu=1 \
    --latency-wait 120 \
    --rerun-incomplete \
    --keep-going \
    --printshellcmds \
    --nolock \
    "${TARGETS[@]}"


# Final validation: every requested target must exist and be nonempty.
MISSING=0

for target in "${TARGETS[@]}"; do
    if [[ ! -s "$target" ]]; then
        echo "MISSING TARGET: $target"
        MISSING=$((MISSING + 1))
    fi
done

if [[ "$MISSING" -ne 0 ]]; then
    echo "ERROR: $MISSING requested targets are missing."
    exit 1
fi

touch "$CONFIG_DIR/COMPLETED"

cat >> "$CONFIG_DIR/job_${SLURM_JOB_ID}.txt" <<EOF
completed=$(date)
status=success
EOF

echo
echo "Configuration completed successfully:"
echo "  $CONFIG_NAME"
echo "Finished: $(date)"
SBATCH

chmod +x "$BATCH_DIR/run_one_config.sbatch"


# ============================================================
# Create a separate submission script
#
# Setup itself does not submit anything.
# ============================================================

cat > "$BATCH_DIR/submit.sh" <<'SUBMIT'
#!/usr/bin/env bash
set -euo pipefail

BATCH_DIR=$(cd "$(dirname "$0")" && pwd)

CONFIG_TABLE="$BATCH_DIR/configs.tsv"
LOG_DIR="$BATCH_DIR/logs"

mkdir -p "$LOG_DIR"

CONFIG_COUNT=$(
    tail -n +2 "$CONFIG_TABLE" \
    | awk 'NF { count += 1 } END { print count + 0 }'
)

if [[ "$CONFIG_COUNT" -le 0 ]]; then
    echo "ERROR: No configurations found."
    exit 1
fi

# At most two configuration jobs use H100 GPUs simultaneously.
MAX_CONCURRENT="${MAX_CONCURRENT:-2}"

ARRAY_END=$((CONFIG_COUNT - 1))

SUBMISSION=$(
    sbatch \
        --parsable \
        --array="0-${ARRAY_END}%${MAX_CONCURRENT}" \
        --output="$LOG_DIR/%A_%a.out" \
        --error="$LOG_DIR/%A_%a.err" \
        "$BATCH_DIR/run_one_config.sbatch" \
        "$BATCH_DIR"
)

JOB_ID="${SUBMISSION%%;*}"

cat > "$BATCH_DIR/submitted_job.txt" <<EOF
job_id=${JOB_ID}
array=0-${ARRAY_END}%${MAX_CONCURRENT}
config_count=${CONFIG_COUNT}
submitted=$(date)
EOF

echo "Submitted tuning array:"
echo "  Job ID:          $JOB_ID"
echo "  Configurations:  $CONFIG_COUNT"
echo "  Max concurrent:  $MAX_CONCURRENT"
echo
echo "Monitor with:"
echo "  squeue -j $JOB_ID"
SUBMIT

chmod +x "$BATCH_DIR/submit.sh"


# ============================================================
# Validate the generated workflows with dry runs
# ============================================================

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u

micromamba activate "$REPO/conda"
hash -r

unset PYTHONHOME || true
export PYTHONNOUSERSITE=1
export PYTHONPATH="$REPO"

echo
echo "Running one Snakemake dry run per configuration..."

while IFS=$'\t' read -r \
    CONFIG_NAME \
    LEARNING_RATE \
    LAM_GRAPH \
    LAM_ALIGN \
    NEGATIVE_SLOPE
do
    if [[ "$CONFIG_NAME" == "config_name" ]]; then
        continue
    fi

    CONFIG_DIR="$BATCH_DIR/configs/$CONFIG_NAME"

    mapfile -t CONFIG_TARGETS \
        < "$CONFIG_DIR/targets.txt"

    echo
    echo "Dry run: $CONFIG_NAME"

    snakemake \
        --dry-run \
        --snakefile "$CONFIG_DIR/workflow/Snakefile" \
        --cores 8 \
        --resources gpu=1 \
        --nolock \
        "${CONFIG_TARGETS[@]}" \
        > "$CONFIG_DIR/dryrun.txt"

    echo "  passed"

done < "$BATCH_DIR/configs.tsv"


# ============================================================
# Final summary
# ============================================================

echo
echo "============================================================"
echo "Tuning batch prepared successfully"
echo "============================================================"
echo "Batch name:"
echo "  $BATCH_NAME"
echo
echo "Batch directory:"
echo "  $BATCH_DIR"
echo
echo "Result directory:"
echo "  $RESULT_BATCH_ROOT"
echo
echo "No jobs have been submitted yet."
echo
echo "Submit with:"
echo "  bash $BATCH_DIR/submit.sh"
echo
echo "The existing baseline remains untouched:"
echo "  $EVAL_DIR/results_gat"
