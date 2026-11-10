#!/usr/bin/env python

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import anndata
import numpy as np
import pandas as pd
import yaml


ID_COLUMNS = [
    "subsample_size",
    "subsample_seed",
]


OFFICIAL_COMPOSITE_METRICS = [
    "mean_average_precision",
    "avg_silhouette_width",
    "neighbor_conservation",
    "seurat_alignment_score",
    "avg_silhouette_width_batch",
    "graph_connectivity",
]


HIGHER_IS_BETTER = {
    "mean_average_precision",
    "normalized_mutual_info",
    "avg_silhouette_width",
    "avg_silhouette_width_batch",
    "neighbor_conservation",
    "graph_connectivity",
    "seurat_alignment_score",
    "feature_consistency",
}


LOWER_IS_BETTER = {
    "foscttm",
}


METADATA_COLUMNS = {
    "architecture",
    "metrics_path",
    "subsample_size",
    "subsample_seed",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare GAT-GLUE and original GCN-GLUE "
            "on the 10x subsampling experiment."
        )
    )

    parser.add_argument(
        "--gat-targets",
        type=Path,
        default=Path("gat_10x_subsample_targets.txt"),
    )

    parser.add_argument(
        "--gcn-targets",
        type=Path,
        default=Path("gcn_10x_subsample_targets.txt"),
    )

    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("results/benchmark.csv"),
        help=(
            "Official full benchmark CSV used to establish "
            "min/max scaling ranges for composite scores."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results_gat/comparison_10x"),
    )

    parser.add_argument(
        "--runtime-comparable",
        action="store_true",
        help=(
            "Treat runtime as comparable. Use this only when "
            "GCN and GAT ran on matching hardware and software."
        ),
    )

    parser.add_argument(
        "--skip-cell-check",
        action="store_true",
        help="Skip verification of matching cell identities.",
    )

    return parser.parse_args()


def parse_identifiers(path: Path) -> Tuple[int, int]:
    data_configuration = next(
        part
        for part in path.parts
        if part.startswith("subsample_size:")
    )

    size_text, seed_text = data_configuration.split(
        "-subsample_seed:",
        1,
    )

    size = int(
        size_text.split(
            "subsample_size:",
            1,
        )[1]
    )

    seed = int(seed_text)

    return size, seed


def load_target_map(path: Path) -> Dict[Tuple[int, int], Path]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Target list does not exist: {path}"
        )

    targets = [
        Path(line.strip())
        for line in path.read_text().splitlines()
        if line.strip()
    ]

    target_map: Dict[Tuple[int, int], Path] = {}

    for target in targets:
        key = parse_identifiers(target)

        if key in target_map:
            raise RuntimeError(
                f"Duplicate target for size/seed {key}: {target}"
            )

        target_map[key] = target

    return target_map


def data_directory(metrics_path: Path) -> Path:
    parts = list(metrics_path.parts)

    index = next(
        index
        for index, part in enumerate(parts)
        if part.startswith("subsample_size:")
    )

    return Path(*parts[:index + 1])


def read_obs_names(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(str(path))

    adata = anndata.read_h5ad(
        str(path),
        backed="r",
    )

    try:
        names = np.asarray(
            adata.obs_names.astype(str)
        )
    finally:
        file_manager = getattr(
            adata,
            "file",
            None,
        )

        if file_manager is not None:
            file_manager.close()

    return names


def compare_name_arrays(
    first: np.ndarray,
    second: np.ndarray,
) -> Dict[str, object]:
    same_order = np.array_equal(
        first,
        second,
    )

    same_set = (
        set(first.tolist())
        == set(second.tolist())
    )

    return {
        "same_order": same_order,
        "same_set": same_set,
        "first_count": int(first.size),
        "second_count": int(second.size),
    }


def verify_cell_identity(
    key: Tuple[int, int],
    gcn_target: Path,
    gat_target: Path,
) -> Dict[str, object]:
    size, seed = key

    row: Dict[str, object] = {
        "subsample_size": size,
        "subsample_seed": seed,
        "cell_identity_ok": False,
        "error": "",
    }

    gcn_data = data_directory(gcn_target)
    gat_data = data_directory(gat_target)

    try:
        gcn_rna = read_obs_names(
            gcn_data / "rna.h5ad"
        )

        gcn_atac = read_obs_names(
            gcn_data / "atac.h5ad"
        )

        gat_rna = read_obs_names(
            gat_data / "rna.h5ad"
        )

        gat_atac = read_obs_names(
            gat_data / "atac.h5ad"
        )

        comparisons = {
            "gcn_rna_vs_atac": compare_name_arrays(
                gcn_rna,
                gcn_atac,
            ),
            "gat_rna_vs_atac": compare_name_arrays(
                gat_rna,
                gat_atac,
            ),
            "gcn_vs_gat_rna": compare_name_arrays(
                gcn_rna,
                gat_rna,
            ),
            "gcn_vs_gat_atac": compare_name_arrays(
                gcn_atac,
                gat_atac,
            ),
        }

        for name, result in comparisons.items():
            row[f"{name}_same_order"] = result[
                "same_order"
            ]

            row[f"{name}_same_set"] = result[
                "same_set"
            ]

            row[f"{name}_first_count"] = result[
                "first_count"
            ]

            row[f"{name}_second_count"] = result[
                "second_count"
            ]

        row["cell_identity_ok"] = all(
            result["same_order"]
            for result in comparisons.values()
        )

    except Exception as error:
        row["error"] = repr(error)

    return row


def read_metrics(
    path: Path,
    architecture: str,
    problems: List[str],
) -> Optional[Dict[str, object]]:
    size, seed = parse_identifiers(path)

    if not path.is_file():
        problems.append(
            f"MISSING\t{path}"
        )
        return None

    if path.stat().st_size == 0:
        problems.append(
            f"EMPTY\t{path}"
        )
        return None

    try:
        with path.open() as handle:
            values = yaml.safe_load(handle)
    except Exception as error:
        problems.append(
            f"READ_ERROR\t{path}\t{error}"
        )
        return None

    if not isinstance(values, dict):
        problems.append(
            f"INVALID_YAML\t{path}"
        )
        return None

    row: Dict[str, object] = {
        "subsample_size": size,
        "subsample_seed": seed,
        "architecture": architecture,
        "metrics_path": str(path),
    }

    for key, value in values.items():
        if isinstance(value, bool):
            continue

        if isinstance(value, (int, float)):
            row[key] = float(value)

    return row


def benchmark_ranges(
    path: Path,
) -> Tuple[Optional[Dict[str, Tuple[float, float]]], str]:
    if not path.is_file():
        return (
            None,
            (
                "Official composite scores were not calculated "
                f"because benchmark CSV is missing: {path}"
            ),
        )

    reference = pd.read_csv(path)

    ranges: Dict[str, Tuple[float, float]] = {}

    for metric in OFFICIAL_COMPOSITE_METRICS:
        if metric not in reference.columns:
            return (
                None,
                (
                    "Official composite scores were not calculated "
                    f"because {metric} is absent from {path}."
                ),
            )

        values = pd.to_numeric(
            reference[metric],
            errors="coerce",
        ).dropna()

        if values.empty:
            return (
                None,
                (
                    "Official composite scores were not calculated "
                    f"because {metric} has no valid values."
                ),
            )

        lower = float(values.min())
        upper = float(values.max())

        if upper == lower:
            return (
                None,
                (
                    "Official composite scores were not calculated "
                    f"because {metric} has zero scaling range."
                ),
            )

        ranges[metric] = (
            lower,
            upper,
        )

    return (
        ranges,
        (
            "Official composite scores used min/max ranges from "
            f"{path}."
        ),
    )


def minmax_scale(
    values: pd.Series,
    lower: float,
    upper: float,
) -> pd.Series:
    # This intentionally does not clip values.
    # It matches the official GLUE R implementation.
    return (
        values - lower
    ) / (
        upper - lower
    )


def add_official_scores(
    paired: pd.DataFrame,
    ranges: Dict[str, Tuple[float, float]],
) -> pd.DataFrame:
    paired = paired.copy()

    for architecture in [
        "gcn",
        "gat",
    ]:
        scaled: Dict[str, pd.Series] = {}

        for metric in OFFICIAL_COMPOSITE_METRICS:
            column = f"{metric}_{architecture}"

            if column not in paired.columns:
                raise RuntimeError(
                    "Cannot calculate official scores: "
                    f"missing column {column}."
                )

            paired[column] = pd.to_numeric(
                paired[column],
                errors="coerce",
            )

            lower, upper = ranges[metric]

            scaled[metric] = minmax_scale(
                paired[column],
                lower,
                upper,
            )

        paired[f"bio_{architecture}"] = (
            scaled["mean_average_precision"]
            + scaled["avg_silhouette_width"]
            + scaled["neighbor_conservation"]
        ) / 3.0

        paired[f"int_{architecture}"] = (
            scaled["seurat_alignment_score"]
            + scaled["avg_silhouette_width_batch"]
            + scaled["graph_connectivity"]
        ) / 3.0

        paired[f"overall_{architecture}"] = (
            0.6 * paired[f"bio_{architecture}"]
            + 0.4 * paired[f"int_{architecture}"]
        )

    for metric in [
        "bio",
        "int",
        "overall",
    ]:
        paired[
            f"{metric}_gat_minus_gcn"
        ] = (
            paired[f"{metric}_gat"]
            - paired[f"{metric}_gcn"]
        )

        paired[
            f"{metric}_improvement"
        ] = paired[
            f"{metric}_gat_minus_gcn"
        ]

    return paired


def summarize_by_size(
    paired: pd.DataFrame,
) -> pd.DataFrame:
    if paired.empty:
        return pd.DataFrame()

    numeric_columns = [
        column
        for column in paired.select_dtypes(
            include=[np.number]
        ).columns
        if column not in ID_COLUMNS
    ]

    summary = (
        paired
        .groupby("subsample_size")[numeric_columns]
        .agg([
            "mean",
            "std",
            "count",
        ])
    )

    summary.columns = [
        f"{column}_{statistic}"
        for column, statistic in summary.columns
    ]

    return summary.reset_index()


def summarize_long(
    long_metrics: pd.DataFrame,
) -> pd.DataFrame:
    if long_metrics.empty:
        return pd.DataFrame()

    numeric_columns = [
        column
        for column in long_metrics.select_dtypes(
            include=[np.number]
        ).columns
        if column not in ID_COLUMNS
    ]

    summary = (
        long_metrics
        .groupby([
            "architecture",
            "subsample_size",
        ])[numeric_columns]
        .agg([
            "mean",
            "std",
            "count",
        ])
    )

    summary.columns = [
        f"{column}_{statistic}"
        for column, statistic in summary.columns
    ]

    return summary.reset_index()


def main() -> None:
    args = parse_args()

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    gat_targets = load_target_map(
        args.gat_targets
    )

    gcn_targets = load_target_map(
        args.gcn_targets
    )

    if len(gat_targets) != 48:
        raise RuntimeError(
            f"Expected 48 GAT targets, found {len(gat_targets)}."
        )

    if len(gcn_targets) != 48:
        raise RuntimeError(
            f"Expected 48 GCN targets, found {len(gcn_targets)}."
        )

    expected_keys = sorted(
        set(gat_targets)
        | set(gcn_targets)
    )

    missing_target_keys = [
        key
        for key in expected_keys
        if (
            key not in gat_targets
            or key not in gcn_targets
        )
    ]

    if missing_target_keys:
        raise RuntimeError(
            "GAT and GCN target lists do not contain "
            f"matching keys: {missing_target_keys}"
        )

    # --------------------------------------------------------
    # Verify exact cell identity
    # --------------------------------------------------------

    identity_rows: List[Dict[str, object]] = []

    if args.skip_cell_check:
        for size, seed in expected_keys:
            identity_rows.append({
                "subsample_size": size,
                "subsample_seed": seed,
                "cell_identity_ok": True,
                "error": "Cell check skipped by command-line option.",
            })
    else:
        for key in expected_keys:
            identity_rows.append(
                verify_cell_identity(
                    key,
                    gcn_targets[key],
                    gat_targets[key],
                )
            )

    identity = pd.DataFrame(
        identity_rows
    ).sort_values(ID_COLUMNS)

    identity.to_csv(
        args.output_dir / "cell_identity_check.csv",
        index=False,
    )

    valid_identity_keys = {
        (
            int(row.subsample_size),
            int(row.subsample_seed),
        )
        for row in identity.itertuples()
        if bool(row.cell_identity_ok)
    }

    # --------------------------------------------------------
    # Read metrics
    # --------------------------------------------------------

    gat_problems: List[str] = []
    gcn_problems: List[str] = []

    gat_rows: List[Dict[str, object]] = []
    gcn_rows: List[Dict[str, object]] = []

    for key in expected_keys:
        gat_row = read_metrics(
            gat_targets[key],
            "GAT",
            gat_problems,
        )

        if gat_row is not None:
            gat_rows.append(gat_row)

        gcn_row = read_metrics(
            gcn_targets[key],
            "GCN",
            gcn_problems,
        )

        if gcn_row is not None:
            gcn_rows.append(gcn_row)

    gat = pd.DataFrame(gat_rows)
    gcn = pd.DataFrame(gcn_rows)

    if not gat.empty:
        gat = gat.sort_values(ID_COLUMNS)

    if not gcn.empty:
        gcn = gcn.sort_values(ID_COLUMNS)

    gat.to_csv(
        args.output_dir / "gat_10x_metrics.csv",
        index=False,
    )

    gcn.to_csv(
        args.output_dir / "gcn_10x_metrics.csv",
        index=False,
    )

    long_metrics = pd.concat(
        [
            gcn,
            gat,
        ],
        ignore_index=True,
        sort=False,
    )

    long_metrics.to_csv(
        args.output_dir / "metrics_long.csv",
        index=False,
    )

    summarize_long(
        long_metrics
    ).to_csv(
        args.output_dir
        / "summary_raw_by_architecture_and_size.csv",
        index=False,
    )

    (
        args.output_dir / "missing_or_invalid_gat.txt"
    ).write_text(
        "\n".join(gat_problems)
        + ("\n" if gat_problems else "")
    )

    (
        args.output_dir / "missing_or_invalid_gcn.txt"
    ).write_text(
        "\n".join(gcn_problems)
        + ("\n" if gcn_problems else "")
    )

    # --------------------------------------------------------
    # Pair only runs with valid metrics and matching cells
    # --------------------------------------------------------

    if gat.empty or gcn.empty:
        paired = pd.DataFrame()
    else:
        paired = gcn.merge(
            gat,
            on=ID_COLUMNS,
            how="inner",
            suffixes=("_gcn", "_gat"),
        )

        valid_identity = pd.DataFrame(
            [
                {
                    "subsample_size": size,
                    "subsample_seed": seed,
                }
                for size, seed in sorted(
                    valid_identity_keys
                )
            ]
        )

        if valid_identity.empty:
            paired = paired.iloc[0:0]
        else:
            paired = paired.merge(
                valid_identity,
                on=ID_COLUMNS,
                how="inner",
            )

    # --------------------------------------------------------
    # Raw metric differences
    # --------------------------------------------------------

    if not paired.empty:
        common_metrics = sorted(
            (
                set(gcn.columns)
                & set(gat.columns)
            )
            - METADATA_COLUMNS
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

            if metric in HIGHER_IS_BETTER:
                paired[
                    f"{metric}_improvement"
                ] = (
                    paired[gat_column]
                    - paired[gcn_column]
                )

            elif metric in LOWER_IS_BETTER:
                paired[
                    f"{metric}_improvement"
                ] = (
                    paired[gcn_column]
                    - paired[gat_column]
                )

        # Runtime is kept as raw data, but not interpreted by default.
        if (
            args.runtime_comparable
            and "time_gcn" in paired.columns
            and "time_gat" in paired.columns
        ):
            paired["time_improvement"] = (
                paired["time_gcn"]
                - paired["time_gat"]
            )

            paired["time_speedup_gcn_over_gat"] = (
                paired["time_gcn"]
                / paired["time_gat"]
            )

    # --------------------------------------------------------
    # Official GLUE paper composite scores
    # --------------------------------------------------------

    ranges, composite_message = benchmark_ranges(
        args.benchmark
    )

    if (
        ranges is not None
        and not paired.empty
    ):
        try:
            paired = add_official_scores(
                paired,
                ranges,
            )
        except Exception as error:
            composite_message = (
                "Official composite score calculation failed: "
                f"{error}"
            )

    (
        args.output_dir / "composite_score_status.txt"
    ).write_text(
        composite_message + "\n"
    )

    runtime_message = (
        "Runtime comparison enabled: GCN and GAT were declared "
        "to have matching hardware/software."
        if args.runtime_comparable
        else
        "Runtime values are retained but no runtime improvement "
        "or speedup is reported because matching hardware was "
        "not confirmed."
    )

    (
        args.output_dir / "runtime_comparison_status.txt"
    ).write_text(
        runtime_message + "\n"
    )

    paired = paired.sort_values(
        ID_COLUMNS
    ) if not paired.empty else paired

    paired.to_csv(
        args.output_dir
        / "paired_10x_gat_vs_gcn.csv",
        index=False,
    )

    summarize_by_size(
        paired
    ).to_csv(
        args.output_dir
        / "summary_10x_by_size.csv",
        index=False,
    )

    identity_failures = int(
        (~identity["cell_identity_ok"]).sum()
    )

    report_lines = [
        f"Expected GAT targets: {len(gat_targets)}",
        f"Completed GAT metrics: {len(gat)}",
        f"Expected GCN targets: {len(gcn_targets)}",
        f"Completed GCN metrics: {len(gcn)}",
        f"Cell identity checks passed: "
        f"{int(identity['cell_identity_ok'].sum())}",
        f"Cell identity checks failed: {identity_failures}",
        f"Valid paired comparisons: {len(paired)}",
        f"Missing/invalid GAT metrics: {len(gat_problems)}",
        f"Missing/invalid GCN metrics: {len(gcn_problems)}",
        composite_message,
        runtime_message,
    ]

    report = "\n".join(
        report_lines
    ) + "\n"

    (
        args.output_dir / "comparison_status.txt"
    ).write_text(report)

    print(report)

    print("Output files:")

    for path in sorted(
        args.output_dir.iterdir()
    ):
        print(" ", path)


if __name__ == "__main__":
    main()
