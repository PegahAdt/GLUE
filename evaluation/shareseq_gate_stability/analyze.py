#!/usr/bin/env python
"""Analyze completed full SHARE-seq gate sweeps without launching training."""

import argparse
import gzip
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

import experiment as experiment

THRESHOLDS = (0.25, 0.50, 0.75)
POPCOUNT = np.array([bin(value).count("1") for value in range(256)], dtype=np.uint8)


def percentage(count, denominator):
    return 100.0 * count / denominator if denominator else float("nan")


def pairwise_counts(masks):
    packed = np.packbits(masks, axis=1)
    sizes = masks.sum(axis=1, dtype=np.int64)
    records = []
    for first, second in itertools.combinations(range(len(masks)), 2):
        intersection = int(POPCOUNT[np.bitwise_and(packed[first], packed[second])].sum())
        union = int(sizes[first] + sizes[second] - intersection)
        records.append(dict(first=first, second=second, size_a=int(sizes[first]), size_b=int(sizes[second]),
                            intersection_size=intersection, union_size=union,
                            jaccard=intersection / union if union else 1.0,
                            overlap_pct_a=percentage(intersection, sizes[first]),
                            overlap_pct_b=percentage(intersection, sizes[second]), both_empty=union == 0))
    return records


def seed_statistics(masks):
    experiment.require(masks.shape[0] == 3, "Exactly three seeds required")
    pairs = pairwise_counts(masks)
    values = np.array([pair["jaccard"] for pair in pairs])
    recurrence = masks.sum(axis=0)
    union = int((recurrence > 0).sum())
    consensus = int((recurrence >= 2).sum())
    intersection = int((recurrence == 3).sum())
    return dict(jaccard_0_1=values[0], jaccard_0_2=values[1], jaccard_1_2=values[2],
                mean_pairwise_jaccard=values.mean(), sd_pairwise_jaccard=values.std(ddof=0),
                min_pairwise_jaccard=values.min(), max_pairwise_jaccard=values.max(),
                three_seed_intersection_size=intersection, three_seed_union_size=union,
                n_edges_at_least_2_of_3=consensus, pct_edges_at_least_2_of_3=percentage(consensus, masks.shape[1]),
                pct_union_at_least_2_of_3=percentage(consensus, union),
                n_edges_all_3_of_3=intersection, pct_edges_all_3_of_3=percentage(intersection, masks.shape[1]),
                pct_union_all_3_of_3=percentage(intersection, union),
                empty_seed_sets=int((masks.sum(axis=1) == 0).sum()), n_edges=masks.shape[1])


def groups(rows):
    yield "all", "", "", list(range(len(rows)))
    for dimension in experiment.DIMS_A + experiment.DIMS_B:
        indices = [index for index, row in enumerate(rows) if int(row["latent_dim"]) == dimension]
        yield "dimension", dimension, "", indices
        for gate in experiment.GATES:
            selected = sorted([index for index in indices if rows[index]["gate_init"] == gate],
                              key=lambda index: int(rows[index]["model_seed"]))
            yield "dimension_gate_init", dimension, float(gate), selected


def save_figure(figure, directory, name):
    import matplotlib.pyplot as plt
    figure.tight_layout()
    for suffix in ("png", "pdf"):
        figure.savefig(directory / f"{name}.{suffix}", dpi=180)
    plt.close(figure)


def plots(destination, rows, gate_values, counts, seed_summary, pair_tables, recurrence_histogram):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    figures = destination / "plots"
    figures.mkdir()
    palette = dict(zip(experiment.GATES, sns.color_palette("viridis", 4)))
    figure, axes = plt.subplots(4, 4, figsize=(17, 13), sharex=True, sharey=True)
    bins = np.linspace(0, 1, 41)
    for axis, dimension in zip(axes.flat, experiment.DIMS_A + experiment.DIMS_B):
        for index, row in enumerate(rows):
            if int(row["latent_dim"]) == dimension:
                heights, borders = np.histogram(gate_values[index], bins=bins, density=True)
                axis.plot((borders[:-1] + borders[1:]) / 2, heights, color=palette[row["gate_init"]],
                          alpha=0.65, label=row["gate_init"] if row["model_seed"] == "0" else None)
        axis.set_title(f"Dimension {dimension}")
        axis.set_xlabel("Gate value")
        axis.set_ylabel("Density")
    axes.flat[0].legend(title="gate_init")
    save_figure(figure, figures, "gate_distributions")

    figure, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    for axis, threshold in zip(axes, THRESHOLDS):
        subset = counts[counts.threshold == threshold]
        for gate in experiment.GATES:
            selected = subset[subset.gate_init == float(gate)].groupby("latent_dim").pct_below_threshold.agg(["mean", "min", "max"])
            axis.plot(selected.index, selected["mean"], marker="o", color=palette[gate], label=gate)
            axis.fill_between(selected.index, selected["min"], selected["max"], color=palette[gate], alpha=0.15)
        axis.set_xscale("log", base=2)
        axis.set_title(f"Gate < {threshold:.2f}")
        axis.set_xlabel("Embedding dimension (mean and seed range)")
        axis.set_ylabel("Edges below threshold (%)")
    axes[0].legend(title="gate_init")
    save_figure(figure, figures, "percentage_below_threshold")

    figure, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    for axis, threshold in zip(axes, THRESHOLDS):
        subset = seed_summary[seed_summary.threshold == threshold]
        for gate in experiment.GATES:
            selected = subset[subset.gate_init == float(gate)].sort_values("latent_dim")
            axis.errorbar(selected.latent_dim, selected.mean_pairwise_jaccard, yerr=selected.sd_pairwise_jaccard,
                          color=palette[gate], label=gate, marker="o", capsize=2)
        axis.set_xscale("log", base=2)
        axis.set_ylim(-0.03, 1.03)
        axis.set_title(f"Gate < {threshold:.2f}")
        axis.set_xlabel("Embedding dimension")
        axis.set_ylabel("Seed Jaccard (mean ± population SD)")
    axes[0].legend(title="gate_init")
    save_figure(figure, figures, "similarity_vs_dimension")

    figure, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    colors = sns.color_palette("turbo", 16)
    for axis, threshold in zip(axes, THRESHOLDS):
        for color, dimension in zip(colors, experiment.DIMS_A + experiment.DIMS_B):
            selected = seed_summary[(seed_summary.threshold == threshold) & (seed_summary.latent_dim == dimension)].sort_values("gate_init")
            axis.plot(selected.gate_init, selected.mean_pairwise_jaccard, marker="o", color=color, label=str(dimension))
        axis.set_title(f"Gate < {threshold:.2f}")
        axis.set_xlabel("gate_init")
        axis.set_ylabel("Mean seed Jaccard")
        axis.set_ylim(-0.03, 1.03)
    axes[-1].legend(title="Dimension", bbox_to_anchor=(1.03, 1), fontsize=8)
    save_figure(figure, figures, "similarity_vs_gate_init")

    seed_pairs = pair_tables[pair_tables.level == "dimension_gate_init"].copy()
    seed_pairs["seed_pair"] = seed_pairs.seed_a.astype(str) + "/" + seed_pairs.seed_b.astype(str)
    figure, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    for axis, threshold in zip(axes, THRESHOLDS):
        sns.boxplot(data=seed_pairs[seed_pairs.threshold == threshold], x="seed_pair", y="jaccard", ax=axis)
        axis.set_title(f"Gate < {threshold:.2f}")
        axis.set_ylabel("Jaccard across dimension/gate_init groups")
    save_figure(figure, figures, "seed_pair_jaccard")

    figure, axes = plt.subplots(1, 3, figsize=(16, 9))
    for axis, threshold in zip(axes, THRESHOLDS):
        matrix = seed_summary[seed_summary.threshold == threshold].pivot(index="latent_dim", columns="gate_init", values="mean_pairwise_jaccard")
        sns.heatmap(matrix, vmin=0, vmax=1, cmap="viridis", annot=True, fmt=".2f", ax=axis)
        axis.set_title(f"Mean seed Jaccard: gate < {threshold:.2f}")
    save_figure(figure, figures, "seed_jaccard_heatmap")

    labels = [f"{row['latent_dim']}/{row['gate_init']}/{row['model_seed']}" for row in rows]
    for threshold in THRESHOLDS:
        matrix = np.eye(len(rows))
        selected = pair_tables[(pair_tables.level == "all") & (pair_tables.threshold == threshold)]
        for pair in selected.itertuples():
            matrix[pair.first, pair.second] = matrix[pair.second, pair.first] = pair.jaccard
        figure, axis = plt.subplots(figsize=(13, 11))
        sns.heatmap(pd.DataFrame(matrix, index=labels, columns=labels), vmin=0, vmax=1, cmap="viridis",
                    xticklabels=12, yticklabels=12, ax=axis)
        axis.set_title(f"All runs: gate < {threshold:.2f} (dimension/gate_init/seed)")
        save_figure(figure, figures, f"all_run_heatmap_{threshold:.2f}")

    figure, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    hist = recurrence_histogram[recurrence_histogram.level == "dimension_gate_init"]
    for axis, threshold in zip(axes, THRESHOLDS):
        selected = hist[hist.threshold == threshold]
        for gate in experiment.GATES:
            totals = selected[selected.gate_init == float(gate)].groupby("n_low").edge_count.sum()
            axis.plot(totals.index, 100 * totals / totals.sum(), marker="o", color=palette[gate], label=gate)
        axis.set_xticks([0, 1, 2, 3])
        axis.set_title(f"Gate < {threshold:.2f}")
        axis.set_xlabel("Seeds with edge below threshold")
        axis.set_ylabel("Edges (%) pooled over dimensions")
    axes[0].legend(title="gate_init")
    save_figure(figure, figures, "edge_recurrence_across_seeds")


def analyze(destination):
    rows = experiment.read_rows()
    experiment.verify_manifest(rows)
    missing = [row["run_id"] for row in rows if not (Path(row["output_directory"]) / "COMPLETED.json").is_file()]
    experiment.require(not missing, f"Training incomplete: {len(missing)} runs missing completion markers; first: {missing[:5]}")
    experiment.require(not destination.exists(), f"Analysis destination already exists: {destination}")
    audit = experiment.verified_preflight()
    edges = pd.read_csv(experiment.ROOT / "manifests/edges.csv")
    gate_values = np.empty((len(rows), len(edges)), dtype=np.float64)
    for index, row in enumerate(rows):
        experiment.validate_complete(row, audit)
        gates = pd.read_csv(Path(row["output_directory"]) / "gates_nonself.csv.gz")
        gate_values[index] = gates.gate.values
        print(f"Validated {index + 1}/{len(rows)}: {row['run_id']}", flush=True)
    destination.mkdir(parents=True)
    (destination / "low_gate_edges").mkdir()
    edges.to_csv(destination / "edge_universe.csv.gz", index=False)
    distributions, counts, histograms = [], [], []
    for index, row in enumerate(rows):
        metadata = dict(run_id=row["run_id"], latent_dim=int(row["latent_dim"]), gate_init=float(row["gate_init"]), model_seed=int(row["model_seed"]))
        values = gate_values[index]
        quantiles = dict(zip(("min", "q05", "q25", "median", "q75", "q95", "max"), np.quantile(values, [0, .05, .25, .5, .75, .95, 1])))
        distributions.append(dict(metadata, n_edges=len(values), mean=values.mean(), sd=values.std(ddof=1), **quantiles))
        heights, borders = np.histogram(values, bins=np.linspace(0, 1, 101))
        for lower, upper, count in zip(borders[:-1], borders[1:], heights):
            histograms.append(dict(metadata, bin_left=lower, bin_right=upper, edge_count=int(count)))
        for threshold in THRESHOLDS:
            selected = values < threshold
            counts.append(dict(metadata, threshold=threshold, n_edges=len(values), n_below_threshold=int(selected.sum()), pct_below_threshold=100 * selected.mean()))
            identities = edges.loc[selected].copy()
            identities["gate"] = values[selected]
            for key, value in dict(metadata, threshold=threshold).items():
                identities[key] = value
            identities.to_csv(destination / "low_gate_edges" / f"{row['run_id']}_lt_{threshold:.2f}.csv.gz", index=False)
    pd.DataFrame(distributions).to_csv(destination / "gate_distributions.csv", index=False)
    pd.DataFrame(histograms).to_csv(destination / "gate_histograms.csv", index=False)
    counts = pd.DataFrame(counts)
    counts.to_csv(destination / "threshold_counts.csv", index=False)
    pair_tables, summaries, seed_summaries, recurrence_histograms = [], [], [], []
    with gzip.open(destination / "edge_recurrence.csv.gz", "wt") as recurrence_file:
        first_chunk = True
        for threshold in THRESHOLDS:
            masks = gate_values < threshold
            all_pairs = pairwise_counts(masks)
            for level, dimension, gate, indices in groups(rows):
                metadata = dict(level=level, latent_dim=dimension, gate_init=gate, threshold=threshold)
                selected_indices = set(indices)
                pairs = []
                for pair in all_pairs:
                    first, second = pair["first"], pair["second"]
                    if first not in selected_indices or second not in selected_indices:
                        continue
                    named = dict(metadata, **pair)
                    for suffix, index in (("a", first), ("b", second)):
                        named.update({f"run_id_{suffix}": rows[index]["run_id"], f"dimension_{suffix}": int(rows[index]["latent_dim"]),
                                      f"gate_init_{suffix}": float(rows[index]["gate_init"]), f"seed_{suffix}": int(rows[index]["model_seed"])})
                    pairs.append(named)
                pair_tables.extend(pairs)
                values = np.array([pair["jaccard"] for pair in pairs])
                nonempty_values = [pair["jaccard"] for pair in pairs if not pair["both_empty"]]
                recurrence = masks[indices].sum(axis=0)
                summaries.append(dict(metadata, n_runs=len(indices), n_pairs=len(pairs), mean_jaccard=values.mean(),
                                      sd_jaccard=values.std(ddof=0), min_jaccard=values.min(), max_jaccard=values.max(),
                                      both_empty_pairs=sum(pair["both_empty"] for pair in pairs),
                                      mean_nonempty_jaccard=np.mean(nonempty_values) if nonempty_values else float("nan"),
                                      intersection_size=int((recurrence == len(indices)).sum()), union_size=int((recurrence > 0).sum())))
                recurring = edges.copy()
                for key, value in metadata.items():
                    recurring[key] = value
                recurring["n_low"] = recurrence
                recurring["n_runs"] = len(indices)
                recurring["pct_runs_low"] = 100 * recurrence / len(indices)
                recurring.to_csv(recurrence_file, index=False, header=first_chunk)
                first_chunk = False
                for frequency, count in enumerate(np.bincount(recurrence.astype(int), minlength=len(indices) + 1)):
                    recurrence_histograms.append(dict(metadata, n_low=frequency, n_runs=len(indices), edge_count=int(count), pct_edges=percentage(count, len(edges))))
                if level == "dimension_gate_init":
                    seed_summaries.append(dict(metadata, **seed_statistics(masks[indices])))
    pair_tables = pd.DataFrame(pair_tables)
    seed_summaries = pd.DataFrame(seed_summaries)
    recurrence_histograms = pd.DataFrame(recurrence_histograms)
    pair_tables.to_csv(destination / "pairwise_similarity.csv", index=False)
    pd.DataFrame(summaries).to_csv(destination / "group_similarity.csv", index=False)
    seed_summaries.to_csv(destination / "seed_reproducibility.csv", index=False)
    recurrence_histograms.to_csv(destination / "recurrence_histogram.csv", index=False)
    plots(destination, rows, gate_values, counts, seed_summaries, pair_tables, recurrence_histograms)
    experiment.atomic_json(destination / "ANALYSIS_COMPLETE.json", dict(completed_at=experiment.now(), runs=len(rows),
                           nonself_edges=len(edges), thresholds=THRESHOLDS, comparison="gate < threshold",
                           empty_set_jaccard=1, sd_ddof=0, preflight_sha256=experiment.FULL.sha(experiment.PREFLIGHT)))
    print(f"Analysis saved to {destination}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=experiment.ROOT / "analysis")
    analyze(parser.parse_args().output.resolve())
