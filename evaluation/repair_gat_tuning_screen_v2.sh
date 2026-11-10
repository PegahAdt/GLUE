#!/usr/bin/env bash
set -euo pipefail

REPO="/project/6001426/paa40/GlUE_Exp/GLUE"
EVAL="$REPO/evaluation"

OLD_BATCH="$EVAL/gat_tuning_10x/screen_v1"
NEW_BATCH="$EVAL/gat_tuning_10x/screen_v2"

OLD_RESULTS="$EVAL/results_gat_tuning/screen_v1"
NEW_RESULTS="$EVAL/results_gat_tuning/screen_v2"

if [[ ! -d "$OLD_BATCH" ]]; then
    echo "ERROR: Missing old batch:"
    echo "  $OLD_BATCH"
    exit 1
fi

# Never overwrite another tuning attempt.
if [[ -e "$NEW_BATCH" || -e "$NEW_RESULTS" ]]; then
    echo "ERROR: screen_v2 already exists."
    echo "Nothing was changed."
    exit 1
fi

mkdir -p \
    "$NEW_BATCH/configs" \
    "$NEW_BATCH/logs" \
    "$NEW_RESULTS"

cp "$OLD_BATCH/configs.tsv" "$NEW_BATCH/"
cp "$OLD_BATCH/base_commit.txt" "$NEW_BATCH/"
cp "$OLD_BATCH/base_branch.txt" "$NEW_BATCH/"
cp "$OLD_BATCH/run_one_config.sbatch" "$NEW_BATCH/"
cp "$OLD_BATCH/submit.sh" "$NEW_BATCH/"

chmod +x \
    "$NEW_BATCH/run_one_config.sbatch" \
    "$NEW_BATCH/submit.sh"

python - \
    "$OLD_BATCH" \
    "$NEW_BATCH" \
    "$OLD_RESULTS" \
    "$NEW_RESULTS" <<'PY'
from __future__ import annotations

import csv
import re
import shutil
import sys
from pathlib import Path


old_batch = Path(sys.argv[1]).resolve()
new_batch = Path(sys.argv[2]).resolve()
old_results = Path(sys.argv[3]).resolve()
new_results = Path(sys.argv[4]).resolve()

config_table = new_batch / "configs.tsv"

manifest_rows = []


def patch_text_files(root: Path) -> None:
    """Replace all screen_v1 paths with screen_v2 paths."""

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue

        patched = (
            text
            .replace(
                old_results.as_posix(),
                new_results.as_posix()
            )
            .replace(
                old_batch.as_posix(),
                new_batch.as_posix()
            )
        )

        if patched != text:
            path.write_text(patched)


with config_table.open(
    newline="",
    encoding="utf-8"
) as handle:
    reader = csv.DictReader(
        handle,
        delimiter="\t"
    )

    for row in reader:
        config_name = row["config_name"]
        lr = row["lr"]
        lam_graph = row["lam_graph"]
        lam_align = row["lam_align"]
        slope = row["gat_negative_slope"]

        old_config = (
            old_batch
            / "configs"
            / config_name
        )

        new_config = (
            new_batch
            / "configs"
            / config_name
        )

        if not old_config.exists():
            raise RuntimeError(
                f"Missing old configuration: {old_config}"
            )

        new_config.mkdir(
            parents=True,
            exist_ok=False
        )

        shutil.copytree(
            old_config / "workflow",
            new_config / "workflow"
        )

        if (old_config / "parameters.tsv").exists():
            shutil.copy2(
                old_config / "parameters.tsv",
                new_config / "parameters.tsv"
            )

        patch_text_files(
            new_config / "workflow"
        )

        old_target_file = (
            old_config / "targets.txt"
        )

        old_targets = [
            line.strip()
            for line in old_target_file.read_text().splitlines()
            if line.strip()
        ]

        if len(old_targets) != 10:
            raise RuntimeError(
                f"{config_name}: expected 10 targets, "
                f"found {len(old_targets)}"
            )

        correct_parameter_component = (
            f"lam_graph:{lam_graph}"
            f"-lam_align:{lam_align}"
            f"-neg_samples:10"
        )

        new_targets = []

        for old_target in old_targets:
            target = old_target.replace(
                old_results.as_posix(),
                new_results.as_posix()
            )

            # Replace the complete path component beginning
            # with lam_graph, whether the old component was
            # complete or incomplete.
            target, replacement_count = re.subn(
                r"lam_graph:[^/]+",
                correct_parameter_component,
                target,
                count=1
            )

            if replacement_count != 1:
                raise RuntimeError(
                    f"{config_name}: could not repair target:\n"
                    f"{old_target}"
                )

            required_parts = [
                f"lam_graph:{lam_graph}",
                f"lam_align:{lam_align}",
                "neg_samples:10",
            ]

            for required in required_parts:
                if required not in target:
                    raise RuntimeError(
                        f"{config_name}: missing {required} in:\n"
                        f"{target}"
                    )

            new_targets.append(target)

        target_file = new_config / "targets.txt"

        target_file.write_text(
            "\n".join(new_targets) + "\n"
        )

        result_root = (
            new_results
            / config_name
            / "raw"
        )

        result_root.mkdir(
            parents=True,
            exist_ok=False
        )

        manifest_rows.append({
            "config_name": config_name,
            "lr": lr,
            "lam_graph": lam_graph,
            "lam_align": lam_align,
            "gat_negative_slope": slope,
            "result_root": result_root.as_posix(),
            "workflow": (
                new_config
                / "workflow"
            ).as_posix(),
            "target_file": target_file.as_posix(),
            "target_count": len(new_targets),
        })


manifest_path = new_batch / "manifest.tsv"

with manifest_path.open(
    "w",
    newline="",
    encoding="utf-8"
) as handle:
    fieldnames = list(manifest_rows[0].keys())

    writer = csv.DictWriter(
        handle,
        fieldnames=fieldnames,
        delimiter="\t"
    )

    writer.writeheader()
    writer.writerows(manifest_rows)


print("Corrected configurations:")

for row in manifest_rows:
    print(
        f"  {row['config_name']}: "
        f"{row['target_count']} targets"
    )
PY


# Verify that every target contains all three parameters.
echo
echo "Checking corrected target paths..."

while IFS= read -r target_file; do
    count=$(wc -l < "$target_file")

    if [[ "$count" -ne 10 ]]; then
        echo "ERROR: Expected 10 targets:"
        echo "  $target_file"
        exit 1
    fi

    if grep -v \
        -E 'lam_graph:[^/]+-lam_align:[^/]+-neg_samples:10/' \
        "$target_file"
    then
        echo "ERROR: Malformed target detected in:"
        echo "  $target_file"
        exit 1
    fi

done < <(
    find "$NEW_BATCH/configs" \
      -mindepth 2 \
      -maxdepth 2 \
      -name targets.txt \
      | sort
)

echo "All target paths contain lam_graph, lam_align and neg_samples."


# Run a complete Snakemake dry run for every configuration.
SNAKEMAKE="$REPO/conda/bin/snakemake"

echo
echo "Running dry runs..."

while IFS=$'\t' read -r \
    config_name \
    lr \
    lam_graph \
    lam_align \
    slope
do
    if [[ "$config_name" == "config_name" ]]; then
        continue
    fi

    config_dir="$NEW_BATCH/configs/$config_name"

    mapfile -t targets \
        < "$config_dir/targets.txt"

    echo "  $config_name"

    env -u PYTHONHOME \
        PYTHONNOUSERSITE=1 \
        PYTHONPATH="$REPO" \
        "$SNAKEMAKE" \
        --dry-run \
        --snakefile "$config_dir/workflow/Snakefile" \
        --cores 8 \
        --resources gpu=1 \
        --nolock \
        "${targets[@]}" \
        > "$config_dir/dryrun.txt"

done < "$NEW_BATCH/configs.tsv"

echo
echo "============================================================"
echo "screen_v2 created successfully"
echo "============================================================"
echo "Batch:"
echo "  $NEW_BATCH"
echo
echo "Results:"
echo "  $NEW_RESULTS"
echo
echo "The failed screen_v1 data was not modified."
