#!/bin/bash
set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL="$REPO/evaluation"
DATASET="10x-Multiome-Pbmc10k"

ORIGINAL_TARGET_LIST="$EVAL/glue_10x_targets.txt"
GAT_WORKFLOW="$EVAL/workflow_gat_10x"

cd "$REPO"

echo "=== Repository ==="
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"

if [ "$(git branch --show-current)" != "GAT_GLUE" ]; then
    echo "ERROR: Expected branch GAT_GLUE."
    exit 1
fi

if ! grep -q -- "--graph-encoder" \
    evaluation/workflow/scripts/run_GLUE.py
then
    echo "ERROR: run_GLUE.py does not support --graph-encoder."
    exit 1
fi

if [ ! -s "$ORIGINAL_TARGET_LIST" ]; then
    echo "ERROR: Original target list not found:"
    echo "  $ORIGINAL_TARGET_LIST"
    exit 1
fi

mkdir -p \
    "$REPO/logs" \
    "$EVAL/results_gat/comparison_10x"

cd "$EVAL"


# ============================================================
# 1. Generate matching GCN and GAT target lists
# ============================================================

python - <<'PY_TARGETS'
from pathlib import Path
import re

dataset = "10x-Multiome-Pbmc10k"

source = Path("glue_10x_targets.txt")
gcn_output = Path("gcn_10x_subsample_targets.txt")
gat_output = Path("gat_10x_subsample_targets.txt")
reference_output = Path("gat_10x_reference_target.txt")

lines = [
    line.strip()
    for line in source.read_text().splitlines()
    if line.strip()
]

gcn_targets = []

for line in lines:
    if dataset not in line:
        continue

    if not line.endswith("metrics.yaml"):
        continue

    if "subsample_size:" not in line:
        continue

    if "results/raw/" not in line:
        continue

    gcn_targets.append(line)

gcn_targets = sorted(set(gcn_targets))

if len(gcn_targets) != 48:
    raise SystemExit(
        "Expected exactly 48 original 10x subsample targets, "
        f"but found {len(gcn_targets)}."
    )

gat_targets = [
    target.replace(
        "results/raw/",
        "results_gat/raw/",
        1
    )
    for target in gcn_targets
]

gcn_output.write_text(
    "\n".join(gcn_targets) + "\n"
)

gat_output.write_text(
    "\n".join(gat_targets) + "\n"
)

first_target = gat_targets[0]

reference_target, count = re.subn(
    r"/subsample_size:\d+-subsample_seed:\d+/",
    "/original/",
    first_target,
    count=1
)

if count != 1:
    raise SystemExit(
        "Could not derive the full-data reference target."
    )

if not reference_target.endswith("metrics.yaml"):
    raise SystemExit(
        "Unexpected target filename while deriving reference."
    )

reference_target = reference_target[
    :-len("metrics.yaml")
] + "feature_latent.csv"

reference_output.write_text(
    reference_target + "\n"
)

print("Original GCN targets:", len(gcn_targets))
print("New GAT targets:", len(gat_targets))
print("GAT reference target:")
print(reference_target)
PY_TARGETS

echo
echo "=== Target counts ==="
wc -l \
    gcn_10x_subsample_targets.txt \
    gat_10x_subsample_targets.txt \
    gat_10x_reference_target.txt


# ============================================================
# 2. Create an isolated GAT workflow
# ============================================================

rm -rf "$GAT_WORKFLOW"
cp -a workflow "$GAT_WORKFLOW"

python - <<'PY_WORKFLOW'
from pathlib import Path

workflow = Path("workflow_gat_10x")

changed_files = 0

for path in workflow.rglob("*"):
    if not path.is_file():
        continue

    try:
        text = path.read_text()
    except UnicodeDecodeError:
        continue

    updated = text.replace(
        "results/raw",
        "results_gat/raw"
    )

    if updated != text:
        path.write_text(updated)
        changed_files += 1

print(
    "Workflow files redirected to results_gat/raw:",
    changed_files
)

methods = workflow / "rules" / "methods.smk"
text = methods.read_text()

# Support a previous environment-variable patch, if present
text = text.replace(
    "$GLUE_GRAPH_ENCODER",
    "gat"
)

text = text.replace(
    "$GAT_NEGATIVE_SLOPE",
    "0.2"
)

if "--graph-encoder gat" not in text:
    needle = (
        '        "--neg-samples '
        '{wildcards.neg_samples} "'
    )

    replacement = (
        '        "--neg-samples '
        '{wildcards.neg_samples} "\n'
        '        "--graph-encoder gat "\n'
        '        "--gat-negative-slope 0.2 "'
    )

    count = text.count(needle)

    if count != 1:
        raise SystemExit(
            "Expected exactly one GLUE negative-samples "
            f"argument line, but found {count}."
        )

    text = text.replace(
        needle,
        replacement,
        1
    )

methods.write_text(text)

if "--graph-encoder gat" not in methods.read_text():
    raise SystemExit(
        "Failed to add GAT arguments to methods.smk."
    )

print("GAT CLI arguments added to copied workflow.")
PY_WORKFLOW

echo
echo "=== Confirm GAT workflow arguments ==="
grep -n -A4 -B2 \
    -- "--graph-encoder gat" \
    workflow_gat_10x/rules/methods.smk


# ============================================================
# 3. Full-data GAT reference job
# ============================================================

cat > run_10x_gat_reference.sh <<'REFERENCE_EOF'
#!/bin/bash
#SBATCH --job-name=gat10x_ref
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_ref_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_ref_%j.err

set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL="$REPO/evaluation"

cd "$REPO"

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u
micromamba activate "$REPO/conda"
hash -r

unset PYTHONPATH || true
export PYTHONNOUSERSITE=1

export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

cd "$EVAL"

TARGET="$(cat gat_10x_reference_target.txt)"

if [ -z "$TARGET" ]; then
    echo "ERROR: Empty reference target."
    exit 1
fi

echo "Job: $SLURM_JOB_ID"
echo "Branch: $(git -C "$REPO" branch --show-current)"
echo "Commit: $(git -C "$REPO" rev-parse --short HEAD)"
echo "Target: $TARGET"
echo "Started: $(date)"

snakemake \
    -s workflow_gat_10x/Snakefile \
    --configfile config/config.yaml \
    -j1 \
    --printshellcmds \
    --rerun-incomplete \
    --latency-wait 120 \
    --nolock \
    "$TARGET"

test -s "$TARGET"

echo "Reference completed:"
echo "$TARGET"
echo "Finished: $(date)"
REFERENCE_EOF


# ============================================================
# 4. All 48 GAT subsample jobs
#    No % concurrency limit
# ============================================================

cat > run_10x_gat_subsamples.sh <<'ARRAY_EOF'
#!/bin/bash
#SBATCH --job-name=gat10x_sub
#SBATCH --time=48:00:00
#SBATCH --mem=192G
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=h100:1
#SBATCH --array=0-47
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_sub_%A_%a.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_sub_%A_%a.err

set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL="$REPO/evaluation"

cd "$REPO"

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u
micromamba activate "$REPO/conda"
hash -r

unset PYTHONPATH || true
export PYTHONNOUSERSITE=1

export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

cd "$EVAL"

LINE_NUMBER=$((SLURM_ARRAY_TASK_ID + 1))

TARGET="$(
    sed -n "${LINE_NUMBER}p" \
    gat_10x_subsample_targets.txt
)"

if [ -z "$TARGET" ]; then
    echo "ERROR: No target for array task $SLURM_ARRAY_TASK_ID."
    exit 1
fi

echo "Array job: $SLURM_ARRAY_JOB_ID"
echo "Array task: $SLURM_ARRAY_TASK_ID"
echo "Branch: $(git -C "$REPO" branch --show-current)"
echo "Commit: $(git -C "$REPO" rev-parse --short HEAD)"
echo "Target: $TARGET"
echo "Started: $(date)"

snakemake \
    -s workflow_gat_10x/Snakefile \
    --configfile config/config.yaml \
    -j1 \
    --printshellcmds \
    --rerun-incomplete \
    --latency-wait 120 \
    --nolock \
    "$TARGET"

test -s "$TARGET"

echo "Completed:"
echo "$TARGET"
echo "Finished: $(date)"
ARRAY_EOF


# ============================================================
# 5. Compare GAT against existing original GCN metrics
# ============================================================

cat > compare_10x_gat_vs_gcn.py <<'COMPARE_EOF'
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml


GAT_TARGET_FILE = Path(
    "gat_10x_subsample_targets.txt"
)

GCN_TARGET_FILE = Path(
    "gcn_10x_subsample_targets.txt"
)

OUTPUT_DIR = Path(
    "results_gat/comparison_10x"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


ID_COLUMNS = [
    "subsample_size",
    "subsample_seed",
]


LOWER_IS_BETTER = {
    "time",
    "foscttm",
}


def parse_identifiers(path: Path) -> Dict[str, int]:
    data_configuration = next(
        part
        for part in path.parts
        if part.startswith("subsample_size:")
    )

    size_text, seed_text = (
        data_configuration.split(
            "-subsample_seed:",
            1
        )
    )

    size = int(
        size_text.split(
            "subsample_size:",
            1
        )[1]
    )

    seed = int(seed_text)

    return {
        "subsample_size": size,
        "subsample_seed": seed,
    }


def load_metrics(
    path: Path,
    architecture: str,
    missing: List[str],
) -> Optional[Dict[str, object]]:

    if not path.exists():
        missing.append(
            f"MISSING\t{path}"
        )
        return None

    if path.stat().st_size == 0:
        missing.append(
            f"EMPTY\t{path}"
        )
        return None

    try:
        with path.open() as handle:
            values = yaml.safe_load(handle)
    except Exception as error:
        missing.append(
            f"READ_ERROR\t{path}\t{error}"
        )
        return None

    if not isinstance(values, dict):
        missing.append(
            f"INVALID_YAML\t{path}"
        )
        return None

    row: Dict[str, object] = {
        **parse_identifiers(path),
        "architecture": architecture,
        "metrics_path": str(path),
    }

    for key, value in values.items():
        if value is None:
            row[key] = None
        elif isinstance(value, bool):
            continue
        elif isinstance(value, (int, float)):
            row[key] = value

    return row


gat_targets = [
    Path(line)
    for line
    in GAT_TARGET_FILE.read_text().splitlines()
    if line.strip()
]

gcn_targets = [
    Path(line)
    for line
    in GCN_TARGET_FILE.read_text().splitlines()
    if line.strip()
]


if len(gat_targets) != 48:
    raise RuntimeError(
        f"Expected 48 GAT targets, found {len(gat_targets)}."
    )

if len(gcn_targets) != 48:
    raise RuntimeError(
        f"Expected 48 GCN targets, found {len(gcn_targets)}."
    )


missing_gat: List[str] = []
missing_gcn: List[str] = []

gat_rows = []
gcn_rows = []


for path in gat_targets:
    row = load_metrics(
        path,
        "GAT",
        missing_gat,
    )

    if row is not None:
        gat_rows.append(row)


for path in gcn_targets:
    row = load_metrics(
        path,
        "GCN",
        missing_gcn,
    )

    if row is not None:
        gcn_rows.append(row)


gat = pd.DataFrame(gat_rows)
gcn = pd.DataFrame(gcn_rows)


sort_columns = [
    "subsample_size",
    "subsample_seed",
]


if not gat.empty:
    gat = gat.sort_values(sort_columns)

if not gcn.empty:
    gcn = gcn.sort_values(sort_columns)


gat.to_csv(
    OUTPUT_DIR / "gat_10x_metrics.csv",
    index=False,
)

gcn.to_csv(
    OUTPUT_DIR / "gcn_10x_metrics.csv",
    index=False,
)


(OUTPUT_DIR / "missing_gat.txt").write_text(
    "\n".join(missing_gat)
    + ("\n" if missing_gat else "")
)

(OUTPUT_DIR / "missing_gcn.txt").write_text(
    "\n".join(missing_gcn)
    + ("\n" if missing_gcn else "")
)


print("Expected GAT targets:", len(gat_targets))
print("Completed GAT metrics:", len(gat))
print("Expected GCN targets:", len(gcn_targets))
print("Completed GCN metrics:", len(gcn))


if gat.empty or gcn.empty:
    print(
        "No paired comparison can be generated yet."
    )
    raise SystemExit(0)


gat_for_merge = gat.drop(
    columns=[
        "architecture",
        "metrics_path",
    ],
    errors="ignore",
)

gcn_for_merge = gcn.drop(
    columns=[
        "architecture",
        "metrics_path",
    ],
    errors="ignore",
)


paired = gcn_for_merge.merge(
    gat_for_merge,
    on=ID_COLUMNS,
    how="inner",
    suffixes=("_gcn", "_gat"),
)


excluded_metrics = {
    "n_cells",
    "subsample_size",
    "subsample_seed",
}


common_metrics = sorted(
    (
        set(gcn_for_merge.columns)
        & set(gat_for_merge.columns)
    )
    - set(ID_COLUMNS)
    - excluded_metrics
)


for metric in common_metrics:
    gcn_column = f"{metric}_gcn"
    gat_column = f"{metric}_gat"

    if (
        gcn_column not in paired.columns
        or gat_column not in paired.columns
    ):
        continue

    paired[gcn_column] = pd.to_numeric(
        paired[gcn_column],
        errors="coerce",
    )

    paired[gat_column] = pd.to_numeric(
        paired[gat_column],
        errors="coerce",
    )

    paired[
        f"{metric}_gat_minus_gcn"
    ] = (
        paired[gat_column]
        - paired[gcn_column]
    )

    if metric in LOWER_IS_BETTER:
        paired[
            f"{metric}_improvement"
        ] = (
            paired[gcn_column]
            - paired[gat_column]
        )
    else:
        paired[
            f"{metric}_improvement"
        ] = (
            paired[gat_column]
            - paired[gcn_column]
        )


paired = paired.sort_values(sort_columns)

paired.to_csv(
    OUTPUT_DIR / "paired_10x_gat_vs_gcn.csv",
    index=False,
)


numeric_columns = [
    column
    for column in paired.columns
    if (
        column.endswith("_gcn")
        or column.endswith("_gat")
        or column.endswith("_improvement")
        or column.endswith("_gat_minus_gcn")
    )
]


summary = (
    paired
    .groupby("subsample_size")[numeric_columns]
    .agg(["mean", "std", "count"])
)

summary.columns = [
    f"{metric}_{statistic}"
    for metric, statistic in summary.columns
]

summary = summary.reset_index()

summary.to_csv(
    OUTPUT_DIR / "summary_10x_by_size.csv",
    index=False,
)


print("Matched GAT/GCN pairs:", len(paired))
print("Missing or invalid GAT:", len(missing_gat))
print("Missing or invalid GCN:", len(missing_gcn))

print("Compared metrics:")
for metric in common_metrics:
    print(" ", metric)

print("Outputs:")
for path in sorted(OUTPUT_DIR.iterdir()):
    print(" ", path)
COMPARE_EOF


# ============================================================
# 6. Comparison collection job
# ============================================================

cat > collect_10x_gat_comparison.sh <<'COLLECT_EOF'
#!/bin/bash
#SBATCH --job-name=gat10x_cmp
#SBATCH --time=00:30:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_cmp_%j.out
#SBATCH --error=/project/6001426/paa40/GlUE_Exp/GLUE/logs/gat10x_cmp_%j.err

set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"

cd "$REPO"

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u
micromamba activate "$REPO/conda"
hash -r

unset PYTHONPATH || true
export PYTHONNOUSERSITE=1

export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

cd "$REPO/evaluation"

python compare_10x_gat_vs_gcn.py
COLLECT_EOF


chmod +x \
    run_10x_gat_reference.sh \
    run_10x_gat_subsamples.sh \
    collect_10x_gat_comparison.sh


# ============================================================
# 7. Validate generated files
# ============================================================

bash -n run_10x_gat_reference.sh
bash -n run_10x_gat_subsamples.sh
bash -n collect_10x_gat_comparison.sh

python -m py_compile \
    compare_10x_gat_vs_gcn.py


echo
echo "=== Array directive ==="
grep -n '#SBATCH --array' \
    run_10x_gat_subsamples.sh


# ============================================================
# 8. Dry run one GAT target
# ============================================================

set +u
eval "$("$HOME/bin/micromamba" shell hook --shell bash)"
set -u
micromamba activate "$REPO/conda"
hash -r

unset PYTHONPATH || true
export PYTHONNOUSERSITE=1

export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

FIRST_TARGET="$(
    head -n 1 gat_10x_subsample_targets.txt
)"

echo
echo "=== Dry run ==="
echo "$FIRST_TARGET"

snakemake \
    -n \
    -s workflow_gat_10x/Snakefile \
    --configfile config/config.yaml \
    -j1 \
    --printshellcmds \
    "$FIRST_TARGET"


# ============================================================
# 9. Submit chained jobs
# ============================================================

echo
echo "=== Submitting jobs ==="

REFERENCE_RAW="$(
    sbatch --parsable \
    run_10x_gat_reference.sh
)"

REFERENCE_JOB="${REFERENCE_RAW%%;*}"

SUBSAMPLE_RAW="$(
    sbatch --parsable \
    --dependency="afterok:${REFERENCE_JOB}" \
    run_10x_gat_subsamples.sh
)"

SUBSAMPLE_JOB="${SUBSAMPLE_RAW%%;*}"

COMPARISON_RAW="$(
    sbatch --parsable \
    --dependency="afterany:${SUBSAMPLE_JOB}" \
    collect_10x_gat_comparison.sh
)"

COMPARISON_JOB="${COMPARISON_RAW%%;*}"


cat > results_gat/10x_submitted_jobs.txt <<EOF_JOBS
reference_job=${REFERENCE_JOB}
subsample_array_job=${SUBSAMPLE_JOB}
comparison_job=${COMPARISON_JOB}
branch=$(git -C "$REPO" branch --show-current)
commit=$(git -C "$REPO" rev-parse --short HEAD)
submitted=$(date)
EOF_JOBS


echo
echo "Reference job:       $REFERENCE_JOB"
echo "Subsample array job: $SUBSAMPLE_JOB"
echo "Comparison job:      $COMPARISON_JOB"

echo
echo "Saved job IDs:"
echo "  $EVAL/results_gat/10x_submitted_jobs.txt"

echo
echo "Current queue:"
squeue -u "$USER"

echo
echo "The array has no % concurrency limit."
echo "Slurm controls actual simultaneous execution."
