#!/usr/bin/env python3
"""Validate, summarize, plot, and report gate-init performance metrics."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml


ROOT = Path("/project/6001426/paa40/GlUE_Exp/GLUE")
OUT = ROOT / "evaluation/gate_init_sensitivity_metrics"
PLOTS = OUT / "plots"
INVENTORY = ROOT / "evaluation/gate_init_sensitivity_report/run_inventory.csv"
GATES = ROOT / "evaluation/gate_init_sensitivity_report/gate_init_distribution_summary.csv"
METRICS = [
    "mean_average_precision", "normalized_mutual_info", "avg_silhouette_width",
    "avg_silhouette_width_batch", "graph_connectivity", "foscttm",
    "neighbor_conservation", "feature_consistency", "seurat_alignment_score", "time",
]
DIRECTION = {metric: "higher" for metric in METRICS}
DIRECTION.update({"foscttm": "lower", "time": "lower"})
LABEL = {
    "mean_average_precision": "Mean average precision",
    "normalized_mutual_info": "Normalized mutual information",
    "avg_silhouette_width": "Average silhouette width",
    "avg_silhouette_width_batch": "Batch ASW",
    "graph_connectivity": "Graph connectivity",
    "foscttm": "FOSCTTM",
    "neighbor_conservation": "Neighbor conservation",
    "feature_consistency": "Feature consistency",
    "seurat_alignment_score": "Seurat alignment score",
    "time": "Training runtime (hours)",
}
SHORT = {
    "mean_average_precision": "MAP", "normalized_mutual_info": "NMI",
    "avg_silhouette_width": "ASW", "avg_silhouette_width_batch": "Batch ASW",
    "graph_connectivity": "Graph conn.", "foscttm": "FOSCTTM",
    "neighbor_conservation": "Neighbor cons.", "feature_consistency": "Feature cons.",
    "seurat_alignment_score": "Seurat align.", "time": "Runtime (h)",
}
GATE_STATS = ["mean", "median", "q05", "pct_below_050", "pct_below_025", "pct_below_010", "delta_mean"]
GATE_LABEL = {
    "mean": "Final mean gate", "median": "Final median gate", "q05": "Final gate Q05",
    "pct_below_050": "Gates < 0.50 (%)", "pct_below_025": "Gates < 0.25 (%)",
    "pct_below_010": "Gates < 0.10 (%)", "delta_mean": "Final mean - gate_init",
}
GATE_INITS = [0.50, 0.70, 0.90, 0.95, 0.99]
SIZES = [250, 2000, 8000]
SEEDS = [0, 1, 2]


def resolve_path(configured: str) -> Path:
    clean = Path(configured)
    found = [p for p in (clean, Path(configured + "\r")) if p.exists()]
    if len(found) != 1:
        raise RuntimeError(f"Expected exactly one path for {configured!r}: {found}")
    return found[0]


def computed_path(gate: float, size: int, seed: int) -> Path:
    return OUT / "per_run" / f"gate_init_{gate:.2f}" / f"subset_{size}" / f"seed_{seed}" / "metrics.yaml"


def load_master() -> pd.DataFrame:
    inventory = list(csv.DictReader(INVENTORY.open(newline="")))
    if len(inventory) != 45 or any(r["status"] != "complete" for r in inventory):
        raise RuntimeError("Run inventory is not exactly 45 complete runs")
    rows = []
    for rec in inventory:
        gate, size, seed, model_seed = float(rec["gate_init"]), int(rec["subset_size"]), int(rec["seed"]), int(rec["model_seed"])
        run = resolve_path(rec["configured_path"])
        info = yaml.unsafe_load((run / "run_info.yaml").read_text())
        args = info["args"]
        checks = [
            math.isclose(float(args["gate_init"]), gate, abs_tol=1e-12), args.get("graph_encoder") == "gated",
            math.isclose(float(args.get("lam_keep", math.nan)), 0.0, abs_tol=1e-15),
            int(args.get("random_seed", -1)) == model_seed,
            f"subsample_size:{size}-subsample_seed:{seed}" in str(args["input_rna"]),
        ]
        if not all(checks):
            raise RuntimeError(f"Metadata validation failed at {run}")
        existing = run / "metrics.yaml"
        source = existing if existing.is_file() and existing.stat().st_size else computed_path(gate, size, seed)
        if not source.is_file() or not source.stat().st_size:
            raise RuntimeError(f"Missing metrics for {(gate, size, seed)}: {source}")
        raw = yaml.safe_load(source.read_text())
        missing = set(METRICS) - set(raw)
        if missing:
            raise RuntimeError(f"Missing canonical metrics {sorted(missing)} at {source}")
        row = {"gate_init": gate, "subset_size": size, "seed": seed, "model_seed": model_seed,
               "status": "complete", "metric_source": "existing_validated" if source == existing else "computed_from_embeddings",
               "n_cells": int(raw.get("n_cells", 2 * size)), "metrics_path": str(source), "run_path": str(run).replace("\r", r"\r")}
        for metric in METRICS:
            value = float(raw[metric])
            row[metric] = value / 3600 if metric == "time" else value
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["gate_init", "subset_size", "seed"]).reset_index(drop=True)


def summarize(master: pd.DataFrame) -> pd.DataFrame:
    long = master.melt(id_vars=["gate_init", "subset_size", "seed"], value_vars=METRICS,
                       var_name="metric", value_name="value")
    out = long.groupby(["gate_init", "subset_size", "metric"], sort=True).value.agg(
        mean="mean", sd="std", min="min", max="max", n_valid="count").reset_index()
    out["direction"] = out.metric.map(DIRECTION)
    return out.sort_values(["subset_size", "metric", "gate_init"]).reset_index(drop=True)


def deltas(master: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = master[master.gate_init == .95].set_index(["subset_size", "seed"])
    paired = []
    for _, row in master.iterrows():
        b = base.loc[(row.subset_size, row.seed)]
        for metric in METRICS:
            paired.append({"gate_init": row.gate_init, "subset_size": int(row.subset_size), "seed": int(row.seed),
                           "metric": metric, "direction": DIRECTION[metric], "alternative": row[metric],
                           "baseline_095": b[metric], "difference": row[metric] - b[metric]})
    paired = pd.DataFrame(paired).sort_values(["metric", "subset_size", "gate_init", "seed"])
    summary = paired.groupby(["gate_init", "subset_size", "metric", "direction"], sort=True).difference.agg(
        mean_paired_difference="mean", sd_paired_difference="std", min_paired_difference="min",
        max_paired_difference="max", n_pairs="count").reset_index()
    return paired, summary


def ranks(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = []
    for (size, metric), group in summary.groupby(["subset_size", "metric"]):
        ascending = DIRECTION[metric] == "lower"
        for rank, (_, row) in enumerate(group.sort_values(["mean", "gate_init"], ascending=[ascending, True]).iterrows(), 1):
            records.append({"subset_size": int(size), "metric": metric, "direction": DIRECTION[metric],
                            "gate_init": row.gate_init, "mean": row["mean"], "rank": rank})
    rank_df = pd.DataFrame(records).sort_values(["subset_size", "metric", "rank"])
    counts = rank_df.groupby(["subset_size", "gate_init", "rank"]).size().unstack(fill_value=0).reset_index()
    counts.columns = ["subset_size", "gate_init"] + [f"rank_{int(x)}_count" for x in counts.columns[2:]]
    return rank_df, counts


def slug(metric: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", metric.lower()).strip("_")


def metric_plot(master: pd.DataFrame, metric: str, delta=False) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.35), sharex=True)
    base = master[master.gate_init == .95].set_index(["subset_size", "seed"])
    for ax, size in zip(axes, SIZES):
        d = master[master.subset_size == size].copy()
        if delta:
            d[metric] = [r[metric] - base.loc[(size, r.seed), metric] for _, r in d.iterrows()]
        for seed, marker in zip(SEEDS, ["o", "s", "^"]):
            q = d[d.seed == seed]
            ax.scatter(q.gate_init, q[metric], s=28, alpha=.65, marker=marker, label=f"seed {seed}")
        stats = d.groupby("gate_init")[metric].agg(["mean", "std"])
        ax.errorbar(stats.index, stats["mean"], yerr=stats["std"], color="black", marker="D", lw=1.3,
                    capsize=3, label="mean ± SD")
        if delta:
            ax.axhline(0, color="0.45", ls="--", lw=1)
        ax.set(title=f"Subset size {size:,}", xlabel="gate_init", xticks=GATE_INITS)
        if ax is axes[0]:
            ax.set_ylabel(("Change in " if delta else "") + LABEL[metric])
    axes[-1].legend(fontsize=7, loc="best")
    fig.tight_layout()
    name = f"{slug(metric)}_{'delta_vs_095' if delta else 'vs_gate_init'}.png"
    path = PLOTS / name
    fig.savefig(path, dpi=220, bbox_inches="tight"); plt.close(fig)
    return path


def overview(master: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(5, 2, figsize=(10.8, 15.2)); colors = dict(zip(SIZES, sns.color_palette("colorblind", 3)))
    for ax, metric in zip(axes.ravel(), METRICS):
        for size in SIZES:
            stats = master[master.subset_size == size].groupby("gate_init")[metric].agg(["mean", "std"])
            ax.errorbar(stats.index, stats["mean"], yerr=stats["std"], marker="o", capsize=2,
                        color=colors[size], label=f"{size:,}")
        ax.set(title=LABEL[metric], xticks=GATE_INITS, xlabel="gate_init", ylabel="Raw value")
    axes[0, 0].legend(title="Subset size", fontsize=7)
    fig.suptitle("Raw metric sensitivity to gate initialization (mean ± seed SD)", y=.998)
    fig.tight_layout(); path=PLOTS/"all_metrics_overview.png"; fig.savefig(path,dpi=220,bbox_inches="tight"); plt.close(fig); return path


def associations(master: pd.DataFrame) -> tuple[pd.DataFrame, list[Path], pd.DataFrame]:
    gates = pd.read_csv(GATES)
    merged = master.merge(gates[["gate_init", "subset_size", "seed"] + GATE_STATS],
                          on=["gate_init", "subset_size", "seed"], validate="one_to_one")
    records, files = [], []
    palette = dict(zip(SIZES, sns.color_palette("colorblind", 3)))
    for metric in METRICS:
        fig, axes = plt.subplots(2, 4, figsize=(12.2, 6.4)); flat=axes.ravel()
        for ax, stat in zip(flat, GATE_STATS):
            for size in SIZES:
                d=merged[merged.subset_size==size]; ax.scatter(d[stat],d[metric],s=24,alpha=.7,color=palette[size],label=f"{size:,}")
                corr=d[[stat,metric]].corr(method="spearman").iloc[0,1]
                records.append({"metric":metric,"gate_stat":stat,"subset_size":size,"spearman_rho":corr,"n":len(d)})
            all_corr=merged[[stat,metric]].corr(method="spearman").iloc[0,1]
            records.append({"metric":metric,"gate_stat":stat,"subset_size":"all","spearman_rho":all_corr,"n":len(merged)})
            ax.set(xlabel=GATE_LABEL[stat],ylabel=SHORT[metric]); ax.set_title(f"overall rho={all_corr:+.2f}",fontsize=9)
        flat[-1].axis("off"); handles,labels=flat[0].get_legend_handles_labels(); flat[-1].legend(handles,labels,title="Subset size",loc="center")
        fig.suptitle(f"Descriptive gate-performance associations: {LABEL[metric]}"); fig.tight_layout()
        path=PLOTS/f"gate_associations_{slug(metric)}.png"; fig.savefig(path,dpi=210,bbox_inches="tight"); plt.close(fig); files.append(path)
    return merged, files, pd.DataFrame(records)


def tex_escape(value) -> str:
    text=str(value)
    return text.replace("\\",r"\textbackslash{}").replace("_",r"\_").replace("%",r"\%").replace("&",r"\&")


def fmt(metric: str, value: float) -> str:
    return f"{value:.3f}" if metric != "time" else f"{value:.2f}"


def longtable(headers, rows, align) -> str:
    lines=[rf"\begin{{longtable}}{{{align}}}",r"\toprule"," & ".join(headers)+r" \\",r"\midrule",r"\endfirsthead",
           r"\toprule"," & ".join(headers)+r" \\",r"\midrule",r"\endhead"]
    lines += [" & ".join(row)+r" \\" for row in rows]
    lines += [r"\bottomrule",r"\end{longtable}"]
    return "\n".join(lines)


def report(master, summary, delta_summary, rank_df, rank_counts, assoc):
    groups=[METRICS[:5],METRICS[5:]]
    lines=[r"\documentclass[10pt]{article}",r"\usepackage[margin=.65in]{geometry}",r"\usepackage{booktabs,longtable,pdflscape,graphicx,float,array,microtype,fancyhdr}",
           r"\pagestyle{fancy}\fancyhf{}\cfoot{\thepage}\renewcommand{\headrulewidth}{0pt}",
           r"\title{GATED GLUE Gate-Initialization Sensitivity\\\large Performance-Metrics Report}\author{}\date{14 August 2026}\begin{document}\maketitle\vspace{-2em}",
           r"\section{Experiment coverage}",
           r"All 45 metadata-validated final-embedding runs are represented: five gate initializations (0.50, 0.70, 0.90, 0.95, 0.99), three subset sizes (250, 2,000, 8,000), and three matched subsample seeds (0--2), with model seed 0. Nine 0.95 metric files were reused after validation; 36 were computed from saved embeddings only. No model was trained.",
           r"\section{Metrics and evaluation definitions}"]
    for m in METRICS:
        lines.append(rf"\noindent\texttt{{{tex_escape(m)}}}: {LABEL[m]} ({DIRECTION[m]} is better).\\")
    lines.append(r"Cell metrics use the unchanged standard workflow implementation, matching RNA/ATAC univariate representations, cell-type and domain labels, paired FOSCTTM, and Seurat-alignment random state 0. Feature consistency uses 2,000 features, four repeats, and random seed 0 against the standard original full-data GLUE reference. Runtime is training time from run metadata, converted to hours; hardware identity was not recorded consistently, so runtime is descriptive only.")
    for gi,g in enumerate(groups,1):
        rows=[]
        for _,r in master.iterrows(): rows.append([f"{r.gate_init:.2f}",f"{int(r.subset_size):,}",str(int(r.seed))]+[fmt(m,r[m]) for m in g])
        heading = r"\section{Per-run results}" if gi == 1 else ""
        lines += [r"\begin{landscape}",heading+rf"\subsection*{{Per-run metrics, part {gi}}}\footnotesize",
                  longtable(["Init","Size","Seed"]+[SHORT[m] for m in g],rows,"rrr"+"r"*len(g)),r"\normalsize\end{landscape}"]
    for gi,g in enumerate(groups,1):
        rows=[]
        for size in SIZES:
            for gate in GATE_INITS:
                cells=[f"{gate:.2f}",f"{size:,}"]
                for m in g:
                    q=summary[(summary.subset_size==size)&(summary.gate_init==gate)&(summary.metric==m)].iloc[0]
                    best=rank_df[(rank_df.subset_size==size)&(rank_df.metric==m)&(rank_df["rank"]==1)].gate_init.iloc[0]
                    val=rf"${fmt(m,q['mean'])} \pm {fmt(m,q.sd)}$"
                    cells.append(rf"\textbf{{{val}}}" if math.isclose(gate,best) else val)
                rows.append(cells)
        heading = r"\section{Mean $\pm$ SD by gate initialization}" if gi == 1 else ""
        lines += [r"\begin{landscape}",heading+rf"\subsection*{{Seed summaries, part {gi}}}\footnotesize",
                  longtable(["Init","Size"]+[SHORT[m] for m in g],rows,"rr"+"r"*len(g)),r"\normalsize\end{landscape}"]
    lines += [r"\section{Metric sensitivity to gate initialization}",r"\begin{figure}[H]\centering\includegraphics[height=.78\textheight]{plots/all_metrics_overview.png}\caption{All raw metrics versus initialization. Points and error bars are mean $\pm$ sample SD over seeds; panels are not normalized.}\end{figure}"]
    lines.append(r"\section{Changes relative to \texttt{gate\_init} = 0.95}")
    delta_rows=[]
    for _,r in delta_summary[delta_summary.gate_init!=.95].iterrows():
        delta_rows.append([f"{r.gate_init:.2f}",f"{int(r.subset_size):,}",SHORT[r.metric],DIRECTION[r.metric],f"{r.mean_paired_difference:+.4f}",f"{r.sd_paired_difference:.4f}"])
    lines += [r"\small",longtable(["Init","Size","Metric","Better","Mean paired diff.","SD"],delta_rows,"rrllrr"),r"\normalsize",
              r"Differences are alternative minus 0.95 within the identical subset size and seed. Positive differences favor alternatives only for higher-is-better metrics; negative differences favor alternatives for FOSCTTM and runtime."]
    lines += [r"\section{Relationship between gate suppression and integration performance}",
              r"\begin{figure}[H]\centering\includegraphics[width=.98\linewidth]{plots/gate_associations_foscttm.png}\caption{Descriptive associations between gate summaries and FOSCTTM. Colors denote subset size; correlations are not causal tests.}\end{figure}",
              r"\begin{figure}[H]\centering\includegraphics[width=.98\linewidth]{plots/gate_associations_mean_average_precision.png}\caption{Descriptive associations between gate summaries and mean average precision.}\end{figure}"]
    lines.append(r"\section{Subset-size consistency and metric ranks}")
    rank_rows=[]
    for _,r in rank_counts.iterrows(): rank_rows.append([f"{r.gate_init:.2f}",f"{int(r.subset_size):,}"]+[str(int(r.get(f'rank_{k}_count',0))) for k in range(1,6)])
    lines += [longtable(["Init","Size","Rank 1","Rank 2","Rank 3","Rank 4","Rank 5"],rank_rows,"rrrrrrr"),
              r"Ranks use metric-specific direction within subset size. Counts are descriptive and are not a composite score or a claim of universal optimality."]
    # Data-driven concise observations
    best095=[]
    for size in SIZES:
        q=rank_df[(rank_df.subset_size==size)&(rank_df["rank"]==1)]
        best095.append((size,int((q.gate_init==.95).sum())))
    nonruntime=assoc[assoc.metric!="time"]
    strongest=nonruntime.iloc[nonruntime.spearman_rho.abs().argmax()]
    lines += [r"\section{Main observations}",
             rf"Across the 10 performance metrics, initialization 0.95 ranks first for {best095[0][1]}, {best095[1][1]}, and {best095[2][1]} metrics at subset sizes 250, 2,000, and 8,000, respectively. Rank wins alone do not establish an overall optimum. The strongest absolute descriptive gate--performance association in the automated analysis is between {tex_escape(GATE_LABEL[strongest.gate_stat])} and {tex_escape(LABEL[strongest.metric])} at subset {strongest.subset_size}, with Spearman $\rho={strongest.spearman_rho:+.2f}$. These associations confound initialization and subset effects and are not causal.",
             r"Seed-level differences and SDs, rather than cell- or edge-level tests, are emphasized because there are only three matched seed replicates. Whether lower initialization clearly improves conservation or alignment should be judged metric-by-metric and subset-by-subset from the tables and delta plots; no arbitrary composite score is used.",
             r"\section{Validation and reproducibility}",
             r"The analysis validates inventory coverage, run metadata, canonical metric names, finite values, unique run identifiers, exact seed aggregation, matched-seed 0.95 comparisons, metric directions, gate-summary one-to-one merging, and table row counts. Every figure is generated from the master CSV-derived data frame.",r"\end{document}"]
    (OUT/"gate_init_metrics_report.tex").write_text("\n".join(lines))


def validate(master, summary, paired, delta_summary, rank_df, merged):
    expected={(g,s,k) for g in GATE_INITS for s in SIZES for k in SEEDS}
    observed=set(map(tuple,master[["gate_init","subset_size","seed"]].to_records(index=False)))
    assert observed==expected and len(master)==45 and not master.duplicated(["gate_init","subset_size","seed"]).any()
    assert set(master.status)=={"complete"} and set(master.metric_source)=={"existing_validated","computed_from_embeddings"}
    assert master.metric_source.value_counts().to_dict()=={"computed_from_embeddings":36,"existing_validated":9}
    assert np.isfinite(master[METRICS].to_numpy()).all()
    assert len(summary)==15*len(METRICS) and set(summary.n_valid)=={3}
    assert len(paired)==45*len(METRICS) and len(delta_summary)==15*len(METRICS)
    assert (paired[paired.gate_init==.95].difference.abs()<1e-14).all()
    assert set(DIRECTION)==set(METRICS) and DIRECTION["foscttm"]==DIRECTION["time"]=="lower"
    assert len(rank_df)==15*len(METRICS) and set(rank_df["rank"])==set(range(1,6))
    assert len(merged)==45 and not merged.duplicated(["gate_init","subset_size","seed"]).any()


def main():
    OUT.mkdir(parents=True,exist_ok=True); PLOTS.mkdir(exist_ok=True)
    master=load_master(); summary=summarize(master); paired,delta_summary=deltas(master); rank_df,rank_counts=ranks(summary)
    master.to_csv(OUT/"gate_init_metrics_by_run.csv",index=False,float_format="%.10g")
    summary.to_csv(OUT/"gate_init_metrics_summary.csv",index=False,float_format="%.10g")
    paired.to_csv(OUT/"gate_init_metric_paired_differences_vs_095.csv",index=False,float_format="%.10g")
    delta_summary.to_csv(OUT/"gate_init_metric_deltas_vs_095.csv",index=False,float_format="%.10g")
    rank_df.to_csv(OUT/"gate_init_metric_ranks.csv",index=False,float_format="%.10g")
    rank_counts.to_csv(OUT/"gate_init_metric_rank_counts.csv",index=False)
    metric_files=[metric_plot(master,m,False) for m in METRICS]
    delta_files=[metric_plot(master,m,True) for m in METRICS]
    overview(master)
    merged,assoc_files,assoc=associations(master)
    merged.to_csv(OUT/"gate_init_metrics_with_gate_distributions.csv",index=False,float_format="%.10g")
    assoc.to_csv(OUT/"gate_metric_associations.csv",index=False,float_format="%.10g")
    validate(master,summary,paired,delta_summary,rank_df,merged)
    report(master,summary,delta_summary,rank_df,rank_counts,assoc)
    print(f"WROTE 45 runs, {len(metric_files)} metric plots, {len(delta_files)} delta plots, {len(assoc_files)} association plots",flush=True)


if __name__=="__main__": main()
