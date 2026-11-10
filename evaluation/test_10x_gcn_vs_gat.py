#!/usr/bin/env python3
from __future__ import annotations

from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


INPUT = Path(
    "results_gat/comparison_10x_gcn_vs_gat/"
    "paired_metrics_long.csv"
)

OUTPUT = Path(
    "results_gat/comparison_10x_gcn_vs_gat"
)

BOOTSTRAP_REPLICATES = 20000
RANDOM_SEED = 20260801


def exact_sign_flip_test(values: np.ndarray) -> float:
    """
    Exact two-sided paired permutation test on the mean difference.

    Under the null hypothesis, changing the signs of paired
    differences should not change their distribution.
    """

    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if len(values) == 0:
        return np.nan

    observed = abs(values.mean())

    signs = np.asarray(
        list(product([-1.0, 1.0], repeat=len(values)))
    )

    null_statistics = np.abs(
        (signs * values).mean(axis=1)
    )

    return float(
        np.mean(
            null_statistics >= observed - 1e-15
        )
    )


def bootstrap_mean_ci(
    values: np.ndarray,
    rng: np.random.Generator
) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if len(values) == 0:
        return np.nan, np.nan

    samples = rng.choice(
        values,
        size=(BOOTSTRAP_REPLICATES, len(values)),
        replace=True
    )

    means = samples.mean(axis=1)

    lower, upper = np.percentile(
        means,
        [2.5, 97.5]
    )

    return float(lower), float(upper)


def holm_adjust(p_values: pd.Series) -> pd.Series:
    """
    Holm family-wise error-rate correction.
    """

    p_values = p_values.astype(float)
    adjusted = pd.Series(
        np.nan,
        index=p_values.index,
        dtype=float
    )

    valid = p_values.dropna().sort_values()
    number_of_tests = len(valid)

    previous = 0.0

    for rank, (index, p_value) in enumerate(
        valid.items()
    ):
        corrected = min(
            1.0,
            (number_of_tests - rank) * p_value
        )

        corrected = max(
            corrected,
            previous
        )

        adjusted.loc[index] = corrected
        previous = corrected

    return adjusted


def summarize_values(
    values: np.ndarray,
    rng: np.random.Generator
) -> dict:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    mean = float(values.mean())
    standard_deviation = (
        float(values.std(ddof=1))
        if len(values) > 1
        else np.nan
    )

    effect_size_dz = (
        mean / standard_deviation
        if standard_deviation > 0
        else np.nan
    )

    ci_lower, ci_upper = bootstrap_mean_ci(
        values,
        rng
    )

    return {
        "n_pairs": len(values),
        "mean_improvement": mean,
        "median_improvement": float(
            np.median(values)
        ),
        "improvement_std": standard_deviation,
        "effect_size_dz": effect_size_dz,
        "ci_95_lower": ci_lower,
        "ci_95_upper": ci_upper,
        "p_exact": exact_sign_flip_test(values),
        "gat_wins": int(np.sum(values > 0)),
        "gcn_wins": int(np.sum(values < 0)),
        "ties": int(np.sum(values == 0)),
    }


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing input file:\n{INPUT}"
        )

    dataframe = pd.read_csv(INPUT)

    # n_cells is metadata rather than a performance metric.
    dataframe = dataframe[
        dataframe["metric"] != "n_cells"
    ].copy()

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    # --------------------------------------------------------
    # Analysis at each subsample size
    # --------------------------------------------------------

    size_rows = []

    for (
        subsample_size,
        metric,
        direction
    ), group in dataframe.groupby(
        [
            "subsample_size",
            "metric",
            "direction",
        ]
    ):
        statistics = summarize_values(
            group["improvement"].to_numpy(),
            rng
        )

        size_rows.append({
            "subsample_size": subsample_size,
            "metric": metric,
            "direction": direction,
            "gcn_mean": group["gcn_value"].mean(),
            "gat_mean": group["gat_value"].mean(),
            **statistics,
        })

    by_size = pd.DataFrame(size_rows)

    # Correct across all size-by-metric tests.
    by_size["p_holm_all"] = holm_adjust(
        by_size["p_exact"]
    )

    # Also correct across the six sizes separately for each metric.
    by_size["p_holm_within_metric"] = (
        by_size
        .groupby("metric")["p_exact"]
        .transform(holm_adjust)
    )

    by_size["significant_holm_all"] = (
        by_size["p_holm_all"] < 0.05
    )

    by_size["significant_within_metric"] = (
        by_size["p_holm_within_metric"] < 0.05
    )

    by_size.sort_values(
        ["metric", "subsample_size"],
        inplace=True
    )

    by_size.to_csv(
        OUTPUT / "significance_by_size.csv",
        index=False
    )

    # --------------------------------------------------------
    # Global analysis clustered by subsample seed
    # --------------------------------------------------------
    #
    # First average each seed's improvements across sizes.
    # This avoids incorrectly treating all 48 runs as fully
    # independent observations.

    seed_level = (
        dataframe
        .groupby(
            [
                "metric",
                "direction",
                "subsample_seed",
            ],
            as_index=False
        )
        .agg(
            seed_mean_improvement=(
                "improvement",
                "mean"
            )
        )
    )

    global_rows = []

    for (
        metric,
        direction
    ), group in seed_level.groupby(
        ["metric", "direction"]
    ):
        statistics = summarize_values(
            group[
                "seed_mean_improvement"
            ].to_numpy(),
            rng
        )

        global_rows.append({
            "metric": metric,
            "direction": direction,
            **statistics,
        })

    global_results = pd.DataFrame(
        global_rows
    )

    global_results["p_holm"] = holm_adjust(
        global_results["p_exact"]
    )

    global_results["significant_holm"] = (
        global_results["p_holm"] < 0.05
    )

    global_results.sort_values(
        "p_exact",
        inplace=True
    )

    global_results.to_csv(
        OUTPUT / "significance_global_by_seed.csv",
        index=False
    )

    print()
    print("=== Global seed-clustered tests ===")
    print(
        global_results[
            [
                "metric",
                "n_pairs",
                "mean_improvement",
                "ci_95_lower",
                "ci_95_upper",
                "effect_size_dz",
                "p_exact",
                "p_holm",
                "significant_holm",
            ]
        ].to_string(index=False)
    )

    print()
    print("Written:")
    print(OUTPUT / "significance_by_size.csv")
    print(
        OUTPUT
        / "significance_global_by_seed.csv"
    )


if __name__ == "__main__":
    main()
