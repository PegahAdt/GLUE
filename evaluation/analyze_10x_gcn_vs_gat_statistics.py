#!/usr/bin/env python3
from __future__ import annotations

import itertools
import math
import re
import warnings
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm
from statsmodels.regression.mixed_linear_model import MixedLM


INPUT_FILE = Path(
    "results_gat/"
    "comparison_10x_gcn_vs_gat/"
    "paired_metrics_long.csv"
)

OUTPUT_DIR = Path(
    "results_gat/"
    "comparison_10x_gcn_vs_gat/"
    "statistical_analysis"
)

MODEL_SUMMARY_DIR = OUTPUT_DIR / "mixed_model_summaries"

BOOTSTRAP_REPLICATES = 20000
RANDOM_SEED = 20260801

# This is metadata, not a performance metric.
EXCLUDED_METRICS = {
    "n_cells",
}


def adjust_pvalues(
    p_values: Sequence[float],
    method: str
) -> np.ndarray:
    """
    Adjust p-values using Holm or Benjamini-Hochberg.

    NaN values are retained as NaN.
    """

    p_values = np.asarray(
        p_values,
        dtype=float
    )

    adjusted = np.full(
        p_values.shape,
        np.nan,
        dtype=float
    )

    valid_indices = np.flatnonzero(
        np.isfinite(p_values)
    )

    if len(valid_indices) == 0:
        return adjusted

    ordered_indices = valid_indices[
        np.argsort(p_values[valid_indices])
    ]

    ordered_p = p_values[ordered_indices]
    number_of_tests = len(ordered_p)

    if method == "holm":
        multipliers = np.arange(
            number_of_tests,
            0,
            -1,
            dtype=float
        )

        ordered_adjusted = (
            ordered_p * multipliers
        )

        ordered_adjusted = np.maximum.accumulate(
            ordered_adjusted
        )

    elif method == "bh":
        ranks = np.arange(
            1,
            number_of_tests + 1,
            dtype=float
        )

        ordered_adjusted = (
            ordered_p
            * number_of_tests
            / ranks
        )

        ordered_adjusted = np.minimum.accumulate(
            ordered_adjusted[::-1]
        )[::-1]

    else:
        raise ValueError(
            f"Unknown adjustment method: {method}"
        )

    adjusted[ordered_indices] = np.clip(
        ordered_adjusted,
        0.0,
        1.0
    )

    return adjusted


def add_grouped_adjustment(
    dataframe: pd.DataFrame,
    p_column: str,
    output_column: str,
    grouping_column: str,
    method: str
) -> None:
    """
    Add p-value correction separately within each group.
    """

    dataframe[output_column] = np.nan

    for _, indices in dataframe.groupby(
        grouping_column
    ).groups.items():

        indices = list(indices)

        corrected = adjust_pvalues(
            dataframe.loc[
                indices,
                p_column
            ].to_numpy(),
            method=method
        )

        dataframe.loc[
            indices,
            output_column
        ] = corrected


def normal_test(
    estimate: float,
    standard_error: float
) -> Tuple[float, float, float, float]:
    """
    Return z statistic, p-value and 95% Wald interval.
    """

    if (
        not np.isfinite(standard_error)
        or standard_error <= 0
    ):
        return (
            np.nan,
            np.nan,
            np.nan,
            np.nan
        )

    z_value = estimate / standard_error

    p_value = 2.0 * norm.sf(
        abs(z_value)
    )

    ci_lower = estimate - 1.96 * standard_error
    ci_upper = estimate + 1.96 * standard_error

    return (
        float(z_value),
        float(p_value),
        float(ci_lower),
        float(ci_upper)
    )


def safe_metric_name(metric: str) -> str:
    return re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        metric
    )


def fit_mixed_model(
    endog: np.ndarray,
    exog: pd.DataFrame,
    groups: np.ndarray
):
    """
    Fit a random-intercept mixed model.

    Several optimizers are attempted because mixed models may
    converge differently depending on the response metric.
    """

    optimizer_methods = [
        "lbfgs",
        "bfgs",
        "cg",
        "powell",
    ]

    successful_results = []
    error_messages = []

    for method in optimizer_methods:
        try:
            model = MixedLM(
                endog=endog,
                exog=exog,
                groups=groups
            )

            with warnings.catch_warnings(
                record=True
            ) as caught_warnings:
                warnings.simplefilter("always")

                result = model.fit(
                    reml=False,
                    method=method,
                    maxiter=5000,
                    disp=False
                )

            warning_messages = [
                str(item.message)
                for item in caught_warnings
            ]

            if np.isfinite(result.llf):
                successful_results.append(
                    (
                        result,
                        method,
                        warning_messages
                    )
                )

                if bool(
                    getattr(
                        result,
                        "converged",
                        False
                    )
                ):
                    return (
                        result,
                        method,
                        warning_messages
                    )

        except Exception as exception:
            error_messages.append(
                f"{method}: {exception}"
            )

    if successful_results:
        # Use the finite result with the highest likelihood.
        best_result = max(
            successful_results,
            key=lambda item: item[0].llf
        )

        return best_result

    raise RuntimeError(
        "All MixedLM optimizers failed:\n"
        + "\n".join(error_messages)
    )


def fixed_effect_covariance(
    result,
    number_of_fixed_effects: int
) -> np.ndarray:
    """
    Extract the covariance matrix of fixed-effect estimates.
    """

    covariance = result.cov_params()

    if hasattr(covariance, "iloc"):
        covariance = covariance.iloc[
            :number_of_fixed_effects,
            :number_of_fixed_effects
        ].to_numpy()
    else:
        covariance = np.asarray(
            covariance,
            dtype=float
        )[
            :number_of_fixed_effects,
            :number_of_fixed_effects
        ]

    return np.asarray(
        covariance,
        dtype=float
    )


def random_intercept_variance(
    result
) -> float:
    covariance = np.asarray(
        result.cov_re,
        dtype=float
    )

    if covariance.size == 0:
        return np.nan

    return float(
        covariance.reshape(-1)[0]
    )


def cluster_bootstrap(
    matrix: np.ndarray,
    rng: np.random.Generator
) -> Tuple[
    Tuple[float, float],
    np.ndarray,
    np.ndarray
]:
    """
    Resample entire seeds with replacement.

    matrix shape:
        number of seeds x number of sizes
    """

    number_of_seeds = matrix.shape[0]

    sampled_indices = rng.integers(
        0,
        number_of_seeds,
        size=(
            BOOTSTRAP_REPLICATES,
            number_of_seeds
        )
    )

    sampled = matrix[
        sampled_indices,
        :
    ]

    size_means = sampled.mean(
        axis=1
    )

    overall_means = size_means.mean(
        axis=1
    )

    overall_ci = tuple(
        np.percentile(
            overall_means,
            [2.5, 97.5]
        ).astype(float)
    )

    size_ci_lower = np.percentile(
        size_means,
        2.5,
        axis=0
    )

    size_ci_upper = np.percentile(
        size_means,
        97.5,
        axis=0
    )

    return (
        overall_ci,
        size_ci_lower,
        size_ci_upper
    )


def exact_cluster_signflip(
    matrix: np.ndarray
) -> Tuple[
    float,
    np.ndarray,
    np.ndarray,
    np.ndarray
]:
    """
    Perform an exact paired permutation test.

    The GCN and GAT labels are swapped at the seed level.
    One sign is applied jointly to all sizes from a seed.

    matrix shape:
        number of seeds x number of sizes
    """

    number_of_seeds = matrix.shape[0]

    if number_of_seeds > 20:
        raise RuntimeError(
            "Exact enumeration is too large for more "
            "than 20 seeds."
        )

    signs = np.asarray(
        list(
            itertools.product(
                [-1.0, 1.0],
                repeat=number_of_seeds
            )
        ),
        dtype=float
    )

    permuted = (
        signs[:, :, np.newaxis]
        * matrix[np.newaxis, :, :]
    )

    null_size_means = permuted.mean(
        axis=1
    )

    null_overall_means = null_size_means.mean(
        axis=1
    )

    observed_size_means = matrix.mean(
        axis=0
    )

    observed_overall_mean = float(
        observed_size_means.mean()
    )

    tolerance = 1e-15

    overall_p = float(
        np.mean(
            np.abs(null_overall_means)
            >= abs(observed_overall_mean)
            - tolerance
        )
    )

    size_p = np.mean(
        np.abs(null_size_means)
        >= (
            np.abs(observed_size_means)
            - tolerance
        )[np.newaxis, :],
        axis=0
    )

    return (
        overall_p,
        np.asarray(
            size_p,
            dtype=float
        ),
        null_overall_means,
        null_size_means
    )


def prepare_dataframe() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file does not exist:\n"
            f"{INPUT_FILE}"
        )

    dataframe = pd.read_csv(
        INPUT_FILE
    )

    required_columns = {
        "subsample_size",
        "subsample_seed",
        "model_seed",
        "metric",
        "direction",
        "gcn_value",
        "gat_value",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise RuntimeError(
            "Input file is missing columns:\n"
            + "\n".join(
                sorted(missing_columns)
            )
        )

    dataframe = dataframe[
        ~dataframe["metric"].isin(
            EXCLUDED_METRICS
        )
    ].copy()

    duplicate_columns = [
        "metric",
        "subsample_size",
        "subsample_seed",
        "model_seed",
    ]

    duplicates = dataframe.duplicated(
        duplicate_columns,
        keep=False
    )

    if duplicates.any():
        raise RuntimeError(
            "Duplicate paired runs were detected:\n"
            + dataframe.loc[
                duplicates,
                duplicate_columns
            ].to_string(index=False)
        )

    model_seeds = sorted(
        dataframe["model_seed"]
        .dropna()
        .unique()
        .tolist()
    )

    if len(model_seeds) != 1:
        raise RuntimeError(
            "This script expects one model seed. "
            f"Found: {model_seeds}"
        )

    # Recompute the direction-adjusted difference rather than
    # relying on a previously calculated column.
    dataframe["raw_improvement"] = np.where(
        dataframe["direction"] == "lower",
        (
            dataframe["gcn_value"]
            - dataframe["gat_value"]
        ),
        (
            dataframe["gat_value"]
            - dataframe["gcn_value"]
        )
    )

    dataframe["analysis_improvement"] = (
        dataframe["raw_improvement"]
    )

    dataframe["analysis_scale"] = "raw_difference"

    # Runtime is positive and typically skewed.
    # Analyze:
    #
    # log(GCN time) - log(GAT time)
    #
    # Positive means GAT is faster.
    time_rows = (
        dataframe["metric"] == "time"
    )

    if time_rows.any():
        if (
            dataframe.loc[
                time_rows,
                [
                    "gcn_value",
                    "gat_value",
                ]
            ] <= 0
        ).any().any():
            raise RuntimeError(
                "Runtime values must be positive "
                "for logarithmic analysis."
            )

        dataframe.loc[
            time_rows,
            "analysis_improvement"
        ] = (
            np.log(
                dataframe.loc[
                    time_rows,
                    "gcn_value"
                ]
            )
            - np.log(
                dataframe.loc[
                    time_rows,
                    "gat_value"
                ]
            )
        )

        dataframe.loc[
            time_rows,
            "analysis_scale"
        ] = "log_runtime_ratio"

    return dataframe


def analyze_metric(
    metric: str,
    metric_data: pd.DataFrame,
    rng: np.random.Generator
) -> Tuple[
    Dict,
    List[Dict],
    Dict,
    List[Dict],
    str
]:
    """
    Analyze one metric using both a mixed model and an exact
    clustered permutation test.
    """

    metric_data = metric_data.copy()

    sizes = sorted(
        int(value)
        for value in metric_data[
            "subsample_size"
        ].unique()
    )

    seeds = sorted(
        int(value)
        for value in metric_data[
            "subsample_seed"
        ].unique()
    )

    expected_pairs = len(sizes) * len(seeds)

    if len(metric_data) != expected_pairs:
        raise RuntimeError(
            f"{metric}: expected {expected_pairs} paired rows "
            f"but found {len(metric_data)}."
        )

    counts = (
        metric_data
        .groupby(
            [
                "subsample_seed",
                "subsample_size",
            ]
        )
        .size()
    )

    if not (counts == 1).all():
        raise RuntimeError(
            f"{metric}: each seed-size combination must "
            "occur exactly once."
        )

    metric_data.sort_values(
        [
            "subsample_seed",
            "subsample_size",
        ],
        inplace=True
    )

    response = metric_data[
        "analysis_improvement"
    ].to_numpy(
        dtype=float
    )

    groups = metric_data[
        "subsample_seed"
    ].to_numpy()

    # One fixed-effect column per size. Each coefficient is the
    # estimated GAT-versus-GCN difference at that size.
    full_design = pd.DataFrame(
        {
            f"size_{size}": (
                metric_data[
                    "subsample_size"
                ].to_numpy()
                == size
            ).astype(float)
            for size in sizes
        },
        index=metric_data.index
    )

    null_design = pd.DataFrame(
        {
            "intercept": np.ones(
                len(metric_data),
                dtype=float
            )
        },
        index=metric_data.index
    )

    (
        full_result,
        full_optimizer,
        full_warnings
    ) = fit_mixed_model(
        endog=response,
        exog=full_design,
        groups=groups
    )

    (
        null_result,
        null_optimizer,
        null_warnings
    ) = fit_mixed_model(
        endog=response,
        exog=null_design,
        groups=groups
    )

    number_of_fixed_effects = len(sizes)

    fixed_effects = np.asarray(
        full_result.fe_params,
        dtype=float
    )

    covariance = fixed_effect_covariance(
        full_result,
        number_of_fixed_effects
    )

    if len(fixed_effects) != number_of_fixed_effects:
        raise RuntimeError(
            f"{metric}: unexpected number of fixed effects."
        )

    # Overall architecture effect, equally averaged across sizes.
    contrast = np.ones(
        number_of_fixed_effects,
        dtype=float
    ) / number_of_fixed_effects

    overall_estimate = float(
        contrast @ fixed_effects
    )

    overall_variance = float(
        contrast
        @ covariance
        @ contrast
    )

    overall_standard_error = math.sqrt(
        max(
            overall_variance,
            0.0
        )
    )

    (
        overall_z,
        overall_p,
        overall_ci_lower,
        overall_ci_upper
    ) = normal_test(
        overall_estimate,
        overall_standard_error
    )

    # Architecture-by-size interaction:
    #
    # H0: the GAT-GCN difference is the same at all sizes.
    likelihood_ratio = max(
        0.0,
        2.0 * (
            float(full_result.llf)
            - float(null_result.llf)
        )
    )

    interaction_degrees_of_freedom = (
        len(sizes) - 1
    )

    interaction_p = float(
        chi2.sf(
            likelihood_ratio,
            interaction_degrees_of_freedom
        )
    )

    analysis_scale = str(
        metric_data[
            "analysis_scale"
        ].iloc[0]
    )

    mixed_overall = {
        "metric": metric,
        "analysis_scale": analysis_scale,
        "n_pairs": len(metric_data),
        "n_seeds": len(seeds),
        "n_sizes": len(sizes),
        "gcn_mean_raw": float(
            metric_data["gcn_value"].mean()
        ),
        "gat_mean_raw": float(
            metric_data["gat_value"].mean()
        ),
        "raw_mean_improvement": float(
            metric_data[
                "raw_improvement"
            ].mean()
        ),
        "model_mean_improvement": overall_estimate,
        "model_standard_error": overall_standard_error,
        "model_ci_95_lower": overall_ci_lower,
        "model_ci_95_upper": overall_ci_upper,
        "model_z": overall_z,
        "model_p_architecture": overall_p,
        "interaction_likelihood_ratio": likelihood_ratio,
        "interaction_df": interaction_degrees_of_freedom,
        "model_p_architecture_by_size": interaction_p,
        "random_intercept_variance": (
            random_intercept_variance(
                full_result
            )
        ),
        "residual_variance": float(
            full_result.scale
        ),
        "full_optimizer": full_optimizer,
        "null_optimizer": null_optimizer,
        "full_converged": bool(
            getattr(
                full_result,
                "converged",
                False
            )
        ),
        "null_converged": bool(
            getattr(
                null_result,
                "converged",
                False
            )
        ),
        "gat_over_gcn_runtime_ratio": (
            float(
                np.exp(
                    -overall_estimate
                )
            )
            if metric == "time"
            else np.nan
        ),
    }

    mixed_by_size = []

    for index, size in enumerate(sizes):
        estimate = float(
            fixed_effects[index]
        )

        standard_error = math.sqrt(
            max(
                float(
                    covariance[index, index]
                ),
                0.0
            )
        )

        (
            z_value,
            p_value,
            ci_lower,
            ci_upper
        ) = normal_test(
            estimate,
            standard_error
        )

        size_data = metric_data[
            metric_data["subsample_size"]
            == size
        ]

        mixed_by_size.append({
            "metric": metric,
            "subsample_size": size,
            "analysis_scale": analysis_scale,
            "n_pairs": len(size_data),
            "gcn_mean_raw": float(
                size_data["gcn_value"].mean()
            ),
            "gcn_std_raw": float(
                size_data["gcn_value"].std(
                    ddof=1
                )
            ),
            "gat_mean_raw": float(
                size_data["gat_value"].mean()
            ),
            "gat_std_raw": float(
                size_data["gat_value"].std(
                    ddof=1
                )
            ),
            "raw_mean_improvement": float(
                size_data[
                    "raw_improvement"
                ].mean()
            ),
            "model_mean_improvement": estimate,
            "model_standard_error": standard_error,
            "model_ci_95_lower": ci_lower,
            "model_ci_95_upper": ci_upper,
            "model_z": z_value,
            "model_p": p_value,
            "gat_over_gcn_runtime_ratio": (
                float(
                    np.exp(
                        -estimate
                    )
                )
                if metric == "time"
                else np.nan
            ),
        })

    # --------------------------------------------------------
    # Exact clustered permutation and clustered bootstrap
    # --------------------------------------------------------

    pivot = (
        metric_data
        .pivot(
            index="subsample_seed",
            columns="subsample_size",
            values="analysis_improvement"
        )
        .reindex(
            index=seeds,
            columns=sizes
        )
    )

    if pivot.isna().any().any():
        raise RuntimeError(
            f"{metric}: incomplete seed-size matrix."
        )

    matrix = pivot.to_numpy(
        dtype=float
    )

    (
        permutation_overall_p,
        permutation_size_p,
        _,
        _
    ) = exact_cluster_signflip(
        matrix
    )

    (
        bootstrap_overall_ci,
        bootstrap_size_ci_lower,
        bootstrap_size_ci_upper
    ) = cluster_bootstrap(
        matrix,
        rng
    )

    permutation_overall = {
        "metric": metric,
        "analysis_scale": analysis_scale,
        "n_seeds": len(seeds),
        "n_sizes": len(sizes),
        "observed_mean_improvement": float(
            matrix.mean()
        ),
        "bootstrap_ci_95_lower": float(
            bootstrap_overall_ci[0]
        ),
        "bootstrap_ci_95_upper": float(
            bootstrap_overall_ci[1]
        ),
        "exact_cluster_permutation_p": (
            permutation_overall_p
        ),
        "number_of_exact_permutations": (
            2 ** len(seeds)
        ),
        "gat_over_gcn_runtime_ratio": (
            float(
                np.exp(
                    -matrix.mean()
                )
            )
            if metric == "time"
            else np.nan
        ),
    }

    permutation_by_size = []

    observed_size_means = matrix.mean(
        axis=0
    )

    for index, size in enumerate(sizes):
        permutation_by_size.append({
            "metric": metric,
            "subsample_size": size,
            "analysis_scale": analysis_scale,
            "n_seeds": len(seeds),
            "observed_mean_improvement": float(
                observed_size_means[index]
            ),
            "bootstrap_ci_95_lower": float(
                bootstrap_size_ci_lower[index]
            ),
            "bootstrap_ci_95_upper": float(
                bootstrap_size_ci_upper[index]
            ),
            "exact_cluster_permutation_p": float(
                permutation_size_p[index]
            ),
            "number_of_exact_permutations": (
                2 ** len(seeds)
            ),
            "gat_over_gcn_runtime_ratio": (
                float(
                    np.exp(
                        -observed_size_means[index]
                    )
                )
                if metric == "time"
                else np.nan
            ),
        })

    warning_text = "\n".join([
        f"Metric: {metric}",
        f"Full optimizer: {full_optimizer}",
        f"Full converged: "
        f"{getattr(full_result, 'converged', False)}",
        "Full-model warnings:",
        *(
            full_warnings
            if full_warnings
            else ["None"]
        ),
        "",
        f"Null optimizer: {null_optimizer}",
        f"Null converged: "
        f"{getattr(null_result, 'converged', False)}",
        "Null-model warnings:",
        *(
            null_warnings
            if null_warnings
            else ["None"]
        ),
        "",
        "Full model summary:",
        str(full_result.summary()),
        "",
        "Null model summary:",
        str(null_result.summary()),
    ])

    return (
        mixed_overall,
        mixed_by_size,
        permutation_overall,
        permutation_by_size,
        warning_text
    )


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    MODEL_SUMMARY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    dataframe = prepare_dataframe()

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    mixed_overall_rows: List[Dict] = []
    mixed_by_size_rows: List[Dict] = []
    permutation_overall_rows: List[Dict] = []
    permutation_by_size_rows: List[Dict] = []

    metrics = sorted(
        dataframe["metric"].unique()
    )

    print("Metrics to analyze:")
    for metric in metrics:
        print(f"  {metric}")

    for metric in metrics:
        print()
        print(f"Analyzing: {metric}")

        metric_data = dataframe[
            dataframe["metric"] == metric
        ].copy()

        (
            mixed_overall,
            mixed_by_size,
            permutation_overall,
            permutation_by_size,
            model_summary
        ) = analyze_metric(
            metric,
            metric_data,
            rng
        )

        mixed_overall_rows.append(
            mixed_overall
        )

        mixed_by_size_rows.extend(
            mixed_by_size
        )

        permutation_overall_rows.append(
            permutation_overall
        )

        permutation_by_size_rows.extend(
            permutation_by_size
        )

        summary_path = (
            MODEL_SUMMARY_DIR
            / (
                safe_metric_name(metric)
                + ".txt"
            )
        )

        summary_path.write_text(
            model_summary,
            encoding="utf-8"
        )

    mixed_overall_df = pd.DataFrame(
        mixed_overall_rows
    )

    mixed_by_size_df = pd.DataFrame(
        mixed_by_size_rows
    )

    permutation_overall_df = pd.DataFrame(
        permutation_overall_rows
    )

    permutation_by_size_df = pd.DataFrame(
        permutation_by_size_rows
    )

    # --------------------------------------------------------
    # Multiple-testing corrections
    # --------------------------------------------------------

    mixed_overall_df[
        "model_p_architecture_bh"
    ] = adjust_pvalues(
        mixed_overall_df[
            "model_p_architecture"
        ].to_numpy(),
        method="bh"
    )

    mixed_overall_df[
        "model_p_architecture_by_size_bh"
    ] = adjust_pvalues(
        mixed_overall_df[
            "model_p_architecture_by_size"
        ].to_numpy(),
        method="bh"
    )

    add_grouped_adjustment(
        mixed_by_size_df,
        p_column="model_p",
        output_column="model_p_holm_within_metric",
        grouping_column="metric",
        method="holm"
    )

    mixed_by_size_df[
        "model_p_bh_all_size_metric_tests"
    ] = adjust_pvalues(
        mixed_by_size_df[
            "model_p"
        ].to_numpy(),
        method="bh"
    )

    permutation_overall_df[
        "exact_cluster_permutation_p_bh"
    ] = adjust_pvalues(
        permutation_overall_df[
            "exact_cluster_permutation_p"
        ].to_numpy(),
        method="bh"
    )

    add_grouped_adjustment(
        permutation_by_size_df,
        p_column="exact_cluster_permutation_p",
        output_column=(
            "exact_cluster_permutation_p_"
            "holm_within_metric"
        ),
        grouping_column="metric",
        method="holm"
    )

    permutation_by_size_df[
        "exact_cluster_permutation_p_"
        "bh_all_size_metric_tests"
    ] = adjust_pvalues(
        permutation_by_size_df[
            "exact_cluster_permutation_p"
        ].to_numpy(),
        method="bh"
    )

    # --------------------------------------------------------
    # Significance flags
    # --------------------------------------------------------

    mixed_overall_df[
        "architecture_significant_bh_0.05"
    ] = (
        mixed_overall_df[
            "model_p_architecture_bh"
        ] < 0.05
    )

    mixed_overall_df[
        "interaction_significant_bh_0.05"
    ] = (
        mixed_overall_df[
            "model_p_architecture_by_size_bh"
        ] < 0.05
    )

    mixed_by_size_df[
        "significant_holm_within_metric_0.05"
    ] = (
        mixed_by_size_df[
            "model_p_holm_within_metric"
        ] < 0.05
    )

    permutation_overall_df[
        "significant_bh_0.05"
    ] = (
        permutation_overall_df[
            "exact_cluster_permutation_p_bh"
        ] < 0.05
    )

    permutation_by_size_df[
        "significant_holm_within_metric_0.05"
    ] = (
        permutation_by_size_df[
            "exact_cluster_permutation_p_"
            "holm_within_metric"
        ] < 0.05
    )

    # Sort output tables.
    mixed_overall_df.sort_values(
        "metric",
        inplace=True
    )

    mixed_by_size_df.sort_values(
        [
            "metric",
            "subsample_size",
        ],
        inplace=True
    )

    permutation_overall_df.sort_values(
        "metric",
        inplace=True
    )

    permutation_by_size_df.sort_values(
        [
            "metric",
            "subsample_size",
        ],
        inplace=True
    )

    # --------------------------------------------------------
    # Save outputs
    # --------------------------------------------------------

    mixed_overall_path = (
        OUTPUT_DIR
        / "mixed_model_overall.csv"
    )

    mixed_by_size_path = (
        OUTPUT_DIR
        / "mixed_model_by_size.csv"
    )

    permutation_overall_path = (
        OUTPUT_DIR
        / "permutation_overall.csv"
    )

    permutation_by_size_path = (
        OUTPUT_DIR
        / "permutation_by_size.csv"
    )

    analyzed_pairs_path = (
        OUTPUT_DIR
        / "analyzed_paired_metrics.csv"
    )

    mixed_overall_df.to_csv(
        mixed_overall_path,
        index=False
    )

    mixed_by_size_df.to_csv(
        mixed_by_size_path,
        index=False
    )

    permutation_overall_df.to_csv(
        permutation_overall_path,
        index=False
    )

    permutation_by_size_df.to_csv(
        permutation_by_size_path,
        index=False
    )

    dataframe.to_csv(
        analyzed_pairs_path,
        index=False
    )

    # Combined terminal summary.
    terminal_summary = (
        mixed_overall_df[
            [
                "metric",
                "model_mean_improvement",
                "model_ci_95_lower",
                "model_ci_95_upper",
                "model_p_architecture",
                "model_p_architecture_bh",
                "model_p_architecture_by_size",
                "model_p_architecture_by_size_bh",
                "full_converged",
            ]
        ]
        .merge(
            permutation_overall_df[
                [
                    "metric",
                    "exact_cluster_permutation_p",
                    "exact_cluster_permutation_p_bh",
                ]
            ],
            on="metric",
            how="left"
        )
    )

    print()
    print(
        "=== Overall architecture and interaction tests ==="
    )

    print(
        terminal_summary.to_string(
            index=False
        )
    )

    print()
    print("Positive mean improvement means GAT is better.")
    print(
        "For time, the effect is log(GCN time / GAT time)."
    )

    print()
    print("Output files:")
    print(mixed_overall_path)
    print(mixed_by_size_path)
    print(permutation_overall_path)
    print(permutation_by_size_path)
    print(analyzed_pairs_path)
    print(MODEL_SUMMARY_DIR)


if __name__ == "__main__":
    main()
