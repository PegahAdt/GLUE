#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import yaml


# Metrics for which a smaller value indicates better performance.
LOWER_IS_BETTER_TOKENS = (
    "foscttm",
    "runtime",
    "walltime",
    "elapsed",
    "time",
)


def flatten_yaml(
    value: Any,
    prefix: str = ""
) -> Dict[str, float]:
    """
    Convert nested YAML metrics into a flat mapping.

    Example
    -------
    {
        "cell_integration": {
            "nmi": 0.8
        }
    }

    becomes
    {
        "cell_integration.nmi": 0.8
    }
    """

    result: Dict[str, float] = {}

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            result.update(
                flatten_yaml(
                    child,
                    child_prefix
                )
            )

    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            child_prefix = (
                f"{prefix}.{index}"
                if prefix
                else str(index)
            )

            result.update(
                flatten_yaml(
                    child,
                    child_prefix
                )
            )

    elif (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        numeric_value = float(value)

        if math.isfinite(numeric_value):
            result[prefix] = numeric_value

    return result


def extract_integer(
    pattern: str,
    text: str
) -> Optional[int]:
    match = re.search(pattern, text)

    if match is None:
        return None

    return int(match.group(1))


def extract_run_information(
    metric_file: Path
) -> Tuple[int, int, int]:
    """
    Parse run identifiers from the metrics.yaml path.
    """

    path_text = metric_file.as_posix()

    subsample_size = extract_integer(
        r"subsample_size:(\d+)",
        path_text
    )

    subsample_seed = extract_integer(
        r"subsample_seed:(\d+)",
        path_text
    )

    model_seed = extract_integer(
        r"/seed:(\d+)/metrics\.yaml$",
        path_text
    )

    missing = []

    if subsample_size is None:
        missing.append("subsample_size")

    if subsample_seed is None:
        missing.append("subsample_seed")

    if model_seed is None:
        missing.append("model_seed")

    if missing:
        raise RuntimeError(
            "Could not extract "
            + ", ".join(missing)
            + f" from:\n{metric_file}"
        )

    return (
        subsample_size,
        subsample_seed,
        model_seed,
    )


def collect_metrics(
    root: Path,
    architecture: str
) -> pd.DataFrame:
    """
    Find and read every subsample metrics.yaml file.
    """

    if not root.exists():
        raise FileNotFoundError(
            f"{architecture} result directory does not exist:\n"
            f"{root}"
        )

    metric_files = sorted(
        root.rglob("metrics.yaml")
    )

    if not metric_files:
        raise RuntimeError(
            f"No metrics.yaml files found for {architecture} under:\n"
            f"{root}"
        )

    rows: List[Dict[str, Any]] = []

    for metric_file in metric_files:
        (
            subsample_size,
            subsample_seed,
            model_seed,
        ) = extract_run_information(metric_file)

        with metric_file.open(
            "r",
            encoding="utf-8"
        ) as file:
            yaml_content = yaml.safe_load(file)

        if yaml_content is None:
            raise RuntimeError(
                f"Empty metrics file:\n{metric_file}"
            )

        flattened_metrics = flatten_yaml(
            yaml_content
        )

        if not flattened_metrics:
            raise RuntimeError(
                "No numeric metrics were found in:\n"
                f"{metric_file}"
            )

        for metric_name, metric_value in flattened_metrics.items():
            rows.append({
                "architecture": architecture,
                "subsample_size": subsample_size,
                "subsample_seed": subsample_seed,
                "model_seed": model_seed,
                "metric": metric_name,
                "value": metric_value,
                "metric_file": str(metric_file),
            })

    dataframe = pd.DataFrame(rows)

    duplicate_keys = [
        "subsample_size",
        "subsample_seed",
        "model_seed",
        "metric",
    ]

    duplicates = dataframe.duplicated(
        subset=duplicate_keys,
        keep=False
    )

    if duplicates.any():
        duplicate_rows = dataframe.loc[
            duplicates,
            duplicate_keys + ["metric_file"]
        ]

        raise RuntimeError(
            f"Duplicate {architecture} metrics detected:\n"
            f"{duplicate_rows.to_string(index=False)}"
        )

    dataframe.sort_values(
        duplicate_keys,
        inplace=True
    )

    dataframe.reset_index(
        drop=True,
        inplace=True
    )

    return dataframe


def get_run_keys(
    dataframe: pd.DataFrame
) -> Set[Tuple[int, int, int]]:
    keys = dataframe[
        [
            "subsample_size",
            "subsample_seed",
            "model_seed",
        ]
    ].drop_duplicates()

    return {
        (
            int(row.subsample_size),
            int(row.subsample_seed),
            int(row.model_seed),
        )
        for row in keys.itertuples(index=False)
    }


def metric_direction(
    metric_name: str
) -> str:
    """
    Return whether larger or smaller values are better.
    """

    lowered = metric_name.lower()

    if any(
        token in lowered
        for token in LOWER_IS_BETTER_TOKENS
    ):
        return "lower"

    return "higher"


def write_run_list(
    path: Path,
    runs: Set[Tuple[int, int, int]]
) -> None:
    with path.open(
        "w",
        encoding="utf-8"
    ) as file:
        for size, subsample_seed, model_seed in sorted(runs):
            file.write(
                f"size={size}, "
                f"subsample_seed={subsample_seed}, "
                f"model_seed={model_seed}\n"
            )


def summarize(
    paired: pd.DataFrame,
    group_columns: List[str]
) -> pd.DataFrame:
    summary = (
        paired
        .groupby(
            group_columns,
            dropna=False
        )
        .agg(
            n_pairs=(
                "improvement",
                "count"
            ),
            gcn_mean=(
                "gcn_value",
                "mean"
            ),
            gcn_std=(
                "gcn_value",
                "std"
            ),
            gat_mean=(
                "gat_value",
                "mean"
            ),
            gat_std=(
                "gat_value",
                "std"
            ),
            mean_gat_minus_gcn=(
                "gat_minus_gcn",
                "mean"
            ),
            mean_improvement=(
                "improvement",
                "mean"
            ),
            mean_relative_improvement_percent=(
                "relative_improvement_percent",
                "mean"
            ),
            gat_wins=(
                "gat_win",
                "sum"
            ),
            gcn_wins=(
                "gcn_win",
                "sum"
            ),
            ties=(
                "tie",
                "sum"
            ),
        )
        .reset_index()
    )

    summary["gat_win_fraction"] = (
        summary["gat_wins"]
        / summary["n_pairs"]
    )

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Gather and compare GCN-GLUE and "
            "raw-weight GAT-GLUE metrics."
        )
    )

    parser.add_argument(
        "--gcn-root",
        type=Path,
        default=Path(
            "results_gcn_h100/raw/"
            "10x-Multiome-Pbmc10k"
        ),
    )

    parser.add_argument(
        "--gat-root",
        type=Path,
        default=Path(
            "results_gat/raw/"
            "10x-Multiome-Pbmc10k"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "results_gat/"
            "comparison_10x_gcn_vs_gat"
        ),
    )

    args = parser.parse_args()

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print("Collecting GCN metrics from:")
    print(args.gcn_root.resolve())

    gcn = collect_metrics(
        args.gcn_root,
        "GCN"
    )

    print()
    print("Collecting GAT metrics from:")
    print(args.gat_root.resolve())

    gat = collect_metrics(
        args.gat_root,
        "GAT"
    )

    gcn.to_csv(
        args.output_dir / "gcn_metrics_long.csv",
        index=False
    )

    gat.to_csv(
        args.output_dir / "gat_metrics_long.csv",
        index=False
    )

    gcn_runs = get_run_keys(gcn)
    gat_runs = get_run_keys(gat)

    missing_from_gat = gcn_runs - gat_runs
    missing_from_gcn = gat_runs - gcn_runs

    write_run_list(
        args.output_dir / "missing_from_gat.txt",
        missing_from_gat
    )

    write_run_list(
        args.output_dir / "missing_from_gcn.txt",
        missing_from_gcn
    )

    print()
    print("=== Run validation ===")
    print(f"GCN runs: {len(gcn_runs)}")
    print(f"GAT runs: {len(gat_runs)}")
    print(
        "GCN runs missing from GAT: "
        f"{len(missing_from_gat)}"
    )
    print(
        "GAT runs missing from GCN: "
        f"{len(missing_from_gcn)}"
    )

    if missing_from_gat or missing_from_gcn:
        raise RuntimeError(
            "GCN and GAT do not contain identical run sets. "
            "See missing_from_gat.txt and missing_from_gcn.txt."
        )

    pairing_keys = [
        "subsample_size",
        "subsample_seed",
        "model_seed",
        "metric",
    ]

    gcn_pairing = gcn[
        pairing_keys + [
            "value",
            "metric_file",
        ]
    ].rename(
        columns={
            "value": "gcn_value",
            "metric_file": "gcn_metric_file",
        }
    )

    gat_pairing = gat[
        pairing_keys + [
            "value",
            "metric_file",
        ]
    ].rename(
        columns={
            "value": "gat_value",
            "metric_file": "gat_metric_file",
        }
    )

    paired_outer = gcn_pairing.merge(
        gat_pairing,
        on=pairing_keys,
        how="outer",
        indicator=True,
        validate="one_to_one"
    )

    missing_gat_metrics = paired_outer[
        paired_outer["_merge"] == "left_only"
    ].copy()

    missing_gcn_metrics = paired_outer[
        paired_outer["_merge"] == "right_only"
    ].copy()

    missing_gat_metrics.to_csv(
        args.output_dir / "missing_gat_metrics.csv",
        index=False
    )

    missing_gcn_metrics.to_csv(
        args.output_dir / "missing_gcn_metrics.csv",
        index=False
    )

    if (
        not missing_gat_metrics.empty
        or not missing_gcn_metrics.empty
    ):
        raise RuntimeError(
            "The runs match, but their metric names do not. "
            "See missing_gat_metrics.csv and "
            "missing_gcn_metrics.csv."
        )

    paired = paired_outer[
        paired_outer["_merge"] == "both"
    ].copy()

    paired.drop(
        columns=["_merge"],
        inplace=True
    )

    paired["direction"] = paired[
        "metric"
    ].map(metric_direction)

    paired["gat_minus_gcn"] = (
        paired["gat_value"]
        - paired["gcn_value"]
    )

    # Positive improvement always means that GAT is better.
    paired["improvement"] = np.where(
        paired["direction"] == "lower",
        paired["gcn_value"] - paired["gat_value"],
        paired["gat_value"] - paired["gcn_value"]
    )

    paired["relative_improvement_percent"] = np.where(
        paired["gcn_value"].abs() > 1e-12,
        (
            paired["improvement"]
            / paired["gcn_value"].abs()
        ) * 100.0,
        np.nan
    )

    tolerance = 1e-12

    paired["gat_win"] = (
        paired["improvement"] > tolerance
    ).astype(int)

    paired["gcn_win"] = (
        paired["improvement"] < -tolerance
    ).astype(int)

    paired["tie"] = (
        paired["improvement"].abs()
        <= tolerance
    ).astype(int)

    paired["winner"] = np.where(
        paired["gat_win"] == 1,
        "GAT",
        np.where(
            paired["gcn_win"] == 1,
            "GCN",
            "Tie"
        )
    )

    paired.sort_values(
        pairing_keys,
        inplace=True
    )

    paired.to_csv(
        args.output_dir / "paired_metrics_long.csv",
        index=False
    )

    summary_by_size = summarize(
        paired,
        [
            "subsample_size",
            "metric",
            "direction",
        ]
    )

    summary_by_size.sort_values(
        [
            "subsample_size",
            "metric",
        ],
        inplace=True
    )

    summary_by_size.to_csv(
        args.output_dir / "summary_by_size.csv",
        index=False
    )

    summary_overall = summarize(
        paired,
        [
            "metric",
            "direction",
        ]
    )

    summary_overall.sort_values(
        ["metric"],
        inplace=True
    )

    summary_overall.to_csv(
        args.output_dir / "summary_overall.csv",
        index=False
    )

    print()
    print("=== Metric validation ===")
    print(f"GCN numeric metric rows: {len(gcn)}")
    print(f"GAT numeric metric rows: {len(gat)}")
    print(f"Paired metric rows:      {len(paired)}")

    print()
    print("=== Overall GCN versus GAT summary ===")
    print(
        summary_overall.to_string(
            index=False
        )
    )

    print()
    print("Files written to:")
    print(args.output_dir.resolve())


if __name__ == "__main__":
    main()
