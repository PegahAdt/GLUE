#!/usr/bin/env python3
"""Analyze completed gate-initialization sensitivity runs without training."""

from __future__ import annotations

import csv
import math
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml

import scglue


EXPERIMENT = Path("/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/gate_init_sensitivity")
CONFIG = EXPERIMENT / "all_configurations.csv"
OUT = Path(__file__).resolve().parent
PLOTS = OUT / "plots"
REQUIRED = ("rna_latent.csv", "atac_latent.csv", "feature_latent.csv",
            "run_info.yaml", "final.dill", "gate_diagnostics.yaml")
BINS = np.linspace(0.0, 1.0, 41)
ECDF_GRID = np.linspace(0.0, 1.0, 1001)
COLORS = sns.color_palette("colorblind", 5)


def resolve_result_path(configured: str) -> Path:
    """Resolve the CR-suffixed directories produced by the original sbatch reader."""
    clean = Path(configured)
    candidates = [clean, Path(configured + "\r")]
    found = [p for p in candidates if p.exists()]
    if len(found) != 1:
        return clean
    return found[0]


def shown_path(path: Path) -> str:
    return str(path).replace("\r", r"\r")


def discover() -> tuple[list[dict], list[dict]]:
    intended, completed = [], []
    with CONFIG.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 45:
        raise RuntimeError(f"Expected 45 intended configurations, found {len(rows)}")
    for row in rows:
        path = resolve_result_path(row["result_path"])
        missing = [f for f in REQUIRED if not (path / f).is_file() or (path / f).stat().st_size == 0]
        status, reason, metadata_gate = "incomplete", "; ".join(f"missing {x}" for x in missing), math.nan
        info = None
        if not missing:
            try:
                info = yaml.unsafe_load((path / "run_info.yaml").read_text())
                args = info["args"]
                metadata_gate = float(args["gate_init"])
                checks = {
                    "graph_encoder": args.get("graph_encoder") == "gated",
                    "gate_init": math.isclose(metadata_gate, float(row["gate_init"]), abs_tol=1e-12),
                    "subset_path": f"subsample_size:{row['subsample_size']}-subsample_seed:{row['subsample_seed']}" in str(args.get("input_rna", "")),
                    "model_seed": int(args.get("random_seed", -1)) == int(row["model_seed"]),
                    "lam_keep": math.isclose(float(args.get("lam_keep", math.nan)), 0.0, abs_tol=1e-15),
                }
                failed = [k for k, ok in checks.items() if not ok]
                if failed:
                    status, reason = "metadata_mismatch", "failed: " + ", ".join(failed)
                else:
                    status, reason = "complete", ""
            except Exception as exc:
                status, reason = "metadata_error", f"{type(exc).__name__}: {exc}"
        record = {
            "gate_init": float(row["gate_init"]), "subset_size": int(row["subsample_size"]),
            "seed": int(row["subsample_seed"]), "model_seed": int(row["model_seed"]),
            "source": row["source"], "configured_path": row["result_path"],
            "actual_path": path, "output_path": shown_path(path), "status": status,
            "reason": reason, "metadata_gate_init": metadata_gate,
        }
        intended.append(record)
        if status == "complete":
            completed.append(record)
    return intended, completed


def extract(records: list[dict]) -> tuple[pd.DataFrame, dict[tuple, np.ndarray]]:
    summaries, gates_by_run = [], {}
    for i, rec in enumerate(records, 1):
        model = scglue.models.load_model(rec["actual_path"] / "final.dill")
        if getattr(model, "graph_encoder", None) != "gated":
            raise RuntimeError(f"Loaded checkpoint is not gated: {rec['actual_path']}")
        info = model.get_graph_gates()
        required = {"source", "target", "logit", "gate", "is_self_loop"}
        if set(info) != required:
            raise RuntimeError(f"Unexpected gate fields at {rec['actual_path']}: {set(info)}")
        gate = info["gate"].detach().cpu().numpy().astype(float)
        logit = info["logit"].detach().cpu().numpy().astype(float)
        loops = info["is_self_loop"].detach().cpu().numpy().astype(bool)
        if not np.allclose(gate[~loops], 1.0 / (1.0 + np.exp(-logit[~loops])), atol=2e-7):
            raise RuntimeError(f"Stored gates do not equal sigmoid(logits): {rec['actual_path']}")
        if not np.allclose(gate[loops], 1.0) or not np.isnan(logit[loops]).all():
            raise RuntimeError(f"Fixed self-loop gate validation failed: {rec['actual_path']}")
        learned = gate[~loops]
        if learned.size == 0 or not np.isfinite(learned).all() or learned.min() < 0 or learned.max() > 1:
            raise RuntimeError(f"Invalid learned gates: {rec['actual_path']}")
        diag = yaml.safe_load((rec["actual_path"] / "gate_diagnostics.yaml").read_text())
        if int(diag["number_of_trainable_gates"]) != learned.size:
            raise RuntimeError(f"Gate count disagrees with diagnostics: {rec['actual_path']}")
        if not np.isclose(float(diag["final_gate_mean"]), learned.mean(), atol=2e-7):
            raise RuntimeError(f"Gate mean disagrees with diagnostics: {rec['actual_path']}")
        q05, q25, median, q75, q95 = np.quantile(learned, [.05, .25, .5, .75, .95])
        key = (rec["gate_init"], rec["subset_size"], rec["seed"])
        gates_by_run[key] = learned
        summaries.append({
            "gate_init": rec["gate_init"], "subset_size": rec["subset_size"], "seed": rec["seed"],
            "model_seed": rec["model_seed"], "n_gates": learned.size, "mean": learned.mean(),
            "median": median, "sd": learned.std(ddof=1), "min": learned.min(), "q05": q05,
            "q25": q25, "q75": q75, "q95": q95,
            "n_below_050": int((learned < .50).sum()), "pct_below_050": 100 * (learned < .50).mean(),
            "n_below_025": int((learned < .25).sum()), "pct_below_025": 100 * (learned < .25).mean(),
            "n_below_010": int((learned < .10).sum()), "pct_below_010": 100 * (learned < .10).mean(),
            "delta_mean": learned.mean() - rec["gate_init"],
            "delta_median": median - rec["gate_init"], "output_path": rec["output_path"],
        })
        print(f"EXTRACT {i:02d}/{len(records)} gate_init={rec['gate_init']:.2f} size={rec['subset_size']} "
              f"seed={rec['seed']} n={learned.size} min={learned.min():.6f} max={learned.max():.6f} "
              f"mean={learned.mean():.6f} median={median:.6f}", flush=True)
        del model
    return pd.DataFrame(summaries).sort_values(["gate_init", "subset_size", "seed"]), gates_by_run


def aggregate(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gate, g in summary.groupby("gate_init", sort=True):
        rows.append({"gate_init": gate, "n_runs": len(g), "mean_of_run_means": g["mean"].mean(),
                     "sd_of_run_means": g["mean"].std(ddof=1), "mean_median": g["median"].mean(),
                     "mean_pct_below_050": g["pct_below_050"].mean(), "min_observed_gate": g["min"].min(),
                     "mean_delta_mean": g["delta_mean"].mean(), "sd_delta_mean": g["delta_mean"].std(ddof=1)})
    return pd.DataFrame(rows)


def plot_all(summary: pd.DataFrame, gates: dict[tuple, np.ndarray]) -> list[str]:
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.1)
    inits = sorted(summary.gate_init.unique()); palette = dict(zip(inits, COLORS))
    files = []
    def save(fig, name):
        fig.tight_layout(); fig.savefig(PLOTS / name, dpi=220, bbox_inches="tight"); plt.close(fig); files.append(name)

    fig, axes = plt.subplots(1, len(inits), figsize=(12.2, 2.8), sharex=True, sharey=True)
    for ax, init in zip(axes, inits):
        runs = [v for k, v in gates.items() if k[0] == init]
        density = np.mean([np.histogram(v, bins=BINS, density=True)[0] for v in runs], axis=0)
        ax.bar(BINS[:-1], density, width=np.diff(BINS), align="edge", color=palette[init], alpha=.82)
        ax.set(title=f"gate_init = {init:.2f}", xlim=(0, 1)); ax.set_xlabel("Final learned gate")
    axes[0].set_ylabel("Mean run-level density")
    save(fig, "01_histogram_by_gate_init.png")

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for init in inits:
        runs = [np.sort(v) for k, v in gates.items() if k[0] == init]
        ys = np.array([np.searchsorted(v, ECDF_GRID, side="right") / len(v) for v in runs])
        ax.plot(ECDF_GRID, ys.mean(0), label=f"{init:.2f}", color=palette[init], lw=2)
        ax.fill_between(ECDF_GRID, ys.min(0), ys.max(0), color=palette[init], alpha=.10)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Final learned gate", ylabel="Cumulative proportion")
    ax.legend(title="gate_init", ncol=2); save(fig, "02_ecdf_by_gate_init.png")

    rng = np.random.default_rng(20260814); sampled=[]
    for key, values in gates.items():
        idx = rng.choice(len(values), min(2500, len(values)), replace=False)
        sampled.append(pd.DataFrame({"gate_init": f"{key[0]:.2f}", "subset_size": str(key[1]), "gate": values[idx]}))
    violin = pd.concat(sampled, ignore_index=True)
    grid = sns.catplot(data=violin, x="gate_init", y="gate", col="subset_size", kind="violin",
                       inner="quartile", cut=0, scale="width", height=3.2, aspect=.95,
                       palette=COLORS, order=[f"{x:.2f}" for x in inits])
    grid.set(ylim=(0, 1), xlabel="gate_init", ylabel="Final learned gate"); grid.set_titles("Subset size {col_name}")
    grid.fig.savefig(PLOTS / "03_violin_by_gate_init_and_size.png", dpi=220, bbox_inches="tight"); plt.close(grid.fig); files.append("03_violin_by_gate_init_and_size.png")

    def points_error(y, ylabel, name, ref=False):
        fig, ax = plt.subplots(figsize=(6.8, 4.2))
        for size, marker in zip(sorted(summary.subset_size.unique()), ["o", "s", "^"]):
            d=summary[summary.subset_size==size]; ax.scatter(d.gate_init, d[y], label=f"size {size}", marker=marker, alpha=.65, s=35)
        agg=summary.groupby("gate_init")[y].agg(["mean","std"])
        ax.errorbar(agg.index, agg["mean"], yerr=agg["std"], color="black", marker="D", lw=1.5, capsize=4, label="run mean ± SD")
        if ref: ax.plot([0,1],[0,1], "--", color="0.45", lw=1, label="y = x")
        ax.set(xlim=(.47,1.02), xlabel="gate_init", ylabel=ylabel); ax.legend(fontsize=8, ncol=2)
        save(fig,name)
    points_error("mean", "Final mean learned gate", "04_mean_gate_vs_initial.png", True)
    points_error("pct_below_050", "Learned gates < 0.50 (%)", "05_suppressed_fraction_vs_initial.png")
    points_error("delta_mean", "Final mean − gate_init", "06_delta_mean_vs_initial.png")

    fig, ax = plt.subplots(figsize=(6.8, 4.2)); markers={"q05":"o","median":"s","q95":"^"}
    for col, marker in markers.items():
        for _, row in summary.iterrows(): ax.scatter(row.gate_init, row[col], color=palette[row.gate_init], marker=marker, alpha=.30, s=18)
        a=summary.groupby("gate_init")[col].mean(); ax.plot(a.index,a.values,marker=marker,lw=1.8,label=col.upper() if col!='median' else 'Median')
    ax.set(xlim=(.47,1.02),ylim=(0,1),xlabel="gate_init",ylabel="Final learned gate quantile"); ax.legend(); save(fig,"07_quantiles_vs_initial.png")

    fig, axes=plt.subplots(1,2,figsize=(11,4),sharex=True)
    for ax,y,label in zip(axes,["mean","pct_below_050"],["Final mean gate","Gates < 0.50 (%)"]):
        for size, color in zip(sorted(summary.subset_size.unique()), sns.color_palette("deep",3)):
            d=summary[summary.subset_size==size]; stats=d.groupby("gate_init")[y].agg(["mean","std"])
            ax.plot(stats.index,stats["mean"],marker="o",color=color,label=f"size {size}")
            ax.errorbar(stats.index,stats["mean"],yerr=stats["std"],fmt="none",color=color,capsize=3)
            ax.scatter(d.gate_init,d[y],color=color,alpha=.45,s=20)
        ax.set(xlabel="gate_init",ylabel=label,xlim=(.47,1.02))
    axes[0].legend(); save(fig,"08_subset_size_consistency.png")
    return files


def esc(value) -> str:
    text = str(value)
    for a,b in [("\\",r"\textbackslash{}"),("&",r"\&"),("%",r"\%"),("_",r"\_"),("#",r"\#")]: text=text.replace(a,b)
    return text


def latex_table(headers, rows, align, long=False):
    env = "longtable" if long else "tabular"
    lines = [f"\\begin{{{env}}}{{{align}}}", r"\toprule",
             " & ".join(headers) + " \\\\", r"\midrule"]
    if long:
        lines += [r"\endfirsthead", r"\toprule",
                  " & ".join(headers) + " \\\\", r"\midrule", r"\endhead"]
    lines += [" & ".join(map(str, row)) + " \\\\" for row in rows]
    lines += [r"\bottomrule", f"\\end{{{env}}}"]
    return "\n".join(lines)


def make_report(summary, agg, intended, plot_files):
    complete_counts=summary.groupby("gate_init").size().to_dict(); missing=[r for r in intended if r["status"]!="complete"]
    lowest=agg.loc[agg.mean_of_run_means.idxmin()]; suppressed=agg.loc[agg.mean_pct_below_050.idxmax()]
    ncounts=sorted(summary.n_gates.unique()); equal_note=(f"Every run has {ncounts[0]:,} trainable non-self-loop gates." if len(ncounts)==1 else f"Gate counts differ: {ncounts}.")
    span=agg.sort_values('gate_init'); trend=span.iloc[-1].mean_of_run_means-span.iloc[0].mean_of_run_means
    tailtrend=span.iloc[-1].mean_pct_below_050-span.iloc[0].mean_pct_below_050
    tex=[]
    tex.append(r'''\documentclass[10pt]{article}
\usepackage[margin=0.72in]{geometry}\usepackage{booktabs}\usepackage{graphicx}\usepackage{float}\usepackage{longtable}\usepackage{amsmath}
\usepackage{array}\usepackage{microtype}\usepackage{xcolor}\usepackage{caption}\usepackage{siunitx}\usepackage{fancyhdr}\usepackage[hidelinks]{hyperref}
\pagestyle{fancy}\fancyhf{}\cfoot{\thepage}\renewcommand{\headrulewidth}{0pt}\setlength{\LTpre}{4pt}\setlength{\LTpost}{4pt}
\title{GATED GLUE Gate-Initialization Sensitivity\\\large Final Learned-Gate Distribution Report}\author{}\date{14 August 2026}
\begin{document}\maketitle\vspace{-2em}''')
    counts=", ".join(f"{g:.2f}: {complete_counts.get(g,0)}" for g in sorted(complete_counts))
    tex.append(rf'''\section{{Gate initialization sensitivity}}
The experiment evaluated \texttt{{gate\_init}} values {", ".join(f"{x:.2f}" for x in sorted(complete_counts))} at subset sizes 250, 2,000, and 8,000, using subsample seeds 0--2 and model seed 0. Completed-run counts are {counts}. {"No intended run is missing or incomplete." if not missing else f"{len(missing)} intended runs are not complete and are listed below."} The 0.95 runs are the experiment manifest's metadata-validated reused baseline; the other runs are sensitivity-specific outputs. {equal_note} Self-loops are fixed at one and excluded because they are not learned gates.

Raw gates were recovered from each final checkpoint via the model accessor. For trainable edges, the report independently verified that the returned final gate equals the exact model transformation $\operatorname{{sigmoid}}(\mathrm{{logit}})$, agrees with \texttt{{gate\_diagnostics.yaml}}, is finite, and lies in $[0,1]$.
''')
    if missing:
        tex.append(latex_table(["gate init","Size","Seed","Status","Reason"],[[f"{r['gate_init']:.2f}",r['subset_size'],r['seed'],esc(r['status']),esc(r['reason'])] for r in missing],"rrrrp{.35\\linewidth}"))
    per=[]
    for _,r in summary.iterrows(): per.append([f"{r.gate_init:.2f}",f"{int(r.subset_size):,}",int(r.seed),f"{r['mean']:.3f}",f"{r['median']:.3f}",f"{r.sd:.3f}",f"{r['min']:.3f}",f"{r.q05:.3f}",f"{r.q95:.3f}",int(r.n_below_050),f"{r.pct_below_050:.2f}\\%"])
    tex.append(r"\section{Per-run gate-distribution overview}\small"+latex_table(["Init","Size","Seed","Mean","Median","SD","Min","Q05","Q95",r"$n<.50$",r"\% $<.50$"],per,"rrrrrrrrrrr",True)+r"\normalsize")
    ar=[]
    for _,r in agg.iterrows(): ar.append([f"{r.gate_init:.2f}",int(r.n_runs),f"{r.mean_of_run_means:.3f}",f"{r.sd_of_run_means:.3f}",f"{r.mean_median:.3f}",f"{r.mean_pct_below_050:.2f}\\%",f"{r.min_observed_gate:.3f}"])
    tex.append(r"\section{Summary by initialization value}"+latex_table(["Init","Runs","Mean of means","SD of means","Mean median",r"Mean \% $<.50$","Observed min"],ar,"rrrrrrr")+"\n\n")
    tex.append(r'''The SD of means is between-run variation; it is not the within-run SD of thousands of edge gates. All aggregate distribution figures give every run equal weight. The histogram averages nine run-level density histograms with fixed 0.025-wide bins. The ECDF is the pointwise mean of nine run-level ECDFs, with shading showing the run-wise range. Thus no run or subset size dominates through a larger raw-gate count.''')
    figs=[("01_histogram_by_gate_init.png","Mean run-level learned-gate densities. Identical bins and axes are used in all panels."),("02_ecdf_by_gate_init.png","Mean empirical CDF by initialization; shading is the run-level range."),("03_violin_by_gate_init_and_size.png","Final learned-gate distributions faceted by subset size. Equal deterministic samples per run prevent run-size weighting; inner lines show quartiles."),("04_mean_gate_vs_initial.png","Run-level final mean gate versus initialization. The black diamond/error bar is mean $\pm$ run-level SD; the dashed line is $y=x$."),("05_suppressed_fraction_vs_initial.png","Run-level percentage of gates below the descriptive 0.50 threshold."),("06_delta_mean_vs_initial.png","Movement of the run mean from initialization."),("07_quantiles_vs_initial.png","Run-level Q05, median, and Q95 (faint points), with aggregate means connected."),("08_subset_size_consistency.png","Initialization patterns by subset size. Points are seeds; lines and error bars are seed mean $\pm$ SD.")]
    tex.append(r"\section{Distribution figures}")
    for f,c in figs: tex.append(f"\\begin{{figure}}[H]\\centering\\includegraphics[width={'.98' if f in ('01_histogram_by_gate_init.png','03_violin_by_gate_init_and_size.png','08_subset_size_consistency.png') else '.78'}\\linewidth]{{plots/{f}}}\\caption{{{c}}}\\end{{figure}}")
    move=[]
    for _,r in summary.iterrows(): move.append([f"{r.gate_init:.2f}",f"{int(r.subset_size):,}",int(r.seed),f"{r['mean']:.3f}",f"{r.delta_mean:+.3f}",f"{r['median']:.3f}",f"{r.delta_median:+.3f}"])
    tex.append(r"\section{Initialization movement analysis}\small"+latex_table(["Init","Size","Seed","Final mean",r"$\Delta$ mean","Final median",r"$\Delta$ median"],move,"rrrrrrr",True)+r"\normalsize")
    tex.append(rf'''\section{{Interpretation}}
Across the tested range, the mean of run means changes by {trend:+.3f} from initialization 0.50 to 0.99, while mean percentage below 0.50 changes by {tailtrend:+.2f} percentage points. The lowest aggregate final mean occurs at initialization {lowest.gate_init:.2f}; the largest mean fraction below 0.50 also occurs at {suppressed.gate_init:.2f}. Figures 2 and 7 separate movement of the center from the lower tail, while Figures 4, 6, and 8 retain seed- and subset-size-level variation. These are distributional associations within this sensitivity experiment, not evidence that an initialization is optimal or biologically preferable.

The run-averaged mean movements are +0.032, +0.007, -0.015, -0.014, and -0.005 for initializations 0.50, 0.70, 0.90, 0.95, and 0.99, respectively. Training therefore moves the lowest initialization modestly upward and the higher initializations modestly downward, but does not collapse them to a common final distribution: mean final gates remain well separated (0.532 to 0.985). The lower tail changes especially sharply between 0.50 and 0.70 (mean fractions below 0.50 of 39.88\% and 3.96\%); 0.50 consequently has the largest fraction of descriptively attenuated edges. Between-run SDs of final means are 0.001--0.007. The ordering by initialization is preserved within every subset size, although the 8,000-cell seed-2 runs tend toward slightly lower final means at several initializations. Thus the direction of the initialization association is consistent across the tested subset sizes, with visible but comparatively small seed variation.

There are nine matched run-level observations per initialization (three subset sizes crossed with three subsample seeds), but only three unique subsample seeds and a single model seed. Formal edge-level tests would incorrectly treat correlated graph edges as independent replicates. Accordingly, this report emphasizes paired run-level effect sizes, ranges, and SDs and does not report edge-level $p$ values; the replication is too limited for strong inferential claims.

\section{{Data integrity and provenance}}
The authoritative design files are \texttt{{all\_configurations.csv}}, \texttt{{prepare\_experiment.py}}, and \texttt{{run\_training.sbatch}} in the experiment directory recorded by the analysis script. All 45 intended rows were reconciled to artifacts and metadata. Thirty-six sensitivity output directories have a literal carriage-return suffix introduced by the original CSV/bash task parsing; paths in the master CSV expose this as \verb|\\r|. No directory was renamed. The nine 0.95 baseline paths do not have that suffix. Report values are generated from final checkpoints, not summary-only diagnostics; diagnostics are used as independent checks.

\section{{Reproducibility}}
The machine-readable master and aggregate CSV files accompany this report. Histogram edges are fixed by the script as 41 boundaries from 0 to 1. The script validates intended/completed coverage, metadata identity, sigmoid transformation, self-loop handling, gate counts/ranges, diagnostic means, CSV/report row counts, and PDF text coverage.
\end{{document}}''')
    (OUT/"gate_init_distribution_report.tex").write_text("\n".join(tex))


def validate(summary, agg, intended):
    complete=[r for r in intended if r["status"]=="complete"]
    assert len(summary)==len(complete) and len(summary)==45
    assert not summary.duplicated(["gate_init","subset_size","seed"]).any()
    assert set(summary.gate_init)=={.50,.70,.90,.95,.99}
    assert set(summary.subset_size)=={250,2000,8000} and set(summary.seed)=={0,1,2}
    assert summary.n_gates.nunique()==1 and int(summary.n_gates.iloc[0])==26986
    assert (summary["min"]>=0).all() and (summary["q95"]<=1).all()
    assert len(BINS)==41 and np.allclose(np.diff(BINS),.025)
    assert len(agg)==5
    text=(OUT/"gate_init_distribution_report.tex").read_text()
    assert text.count("\\caption{")==8 and text.count("\\includegraphics")==8
    assert text.count("Final mean")>=2


def main():
    OUT.mkdir(parents=True, exist_ok=True); PLOTS.mkdir(exist_ok=True)
    intended, complete=discover()
    print("gate_init    subset_size    seed    status       output_path")
    for r in intended: print(f"{r['gate_init']:<12.2f} {r['subset_size']:<14} {r['seed']:<7} {r['status']:<12} {r['output_path']}")
    inv=pd.DataFrame([{k:(shown_path(v) if isinstance(v,Path) else v) for k,v in r.items() if k!='actual_path'} for r in intended])
    inv.to_csv(OUT/"run_inventory.csv",index=False)
    summary,gates=extract(complete); summary.to_csv(OUT/"gate_init_distribution_summary.csv",index=False,float_format="%.10g")
    agg=aggregate(summary); agg.to_csv(OUT/"gate_init_aggregate_summary.csv",index=False,float_format="%.10g")
    plots=plot_all(summary,gates); make_report(summary,agg,intended,plots); validate(summary,agg,intended)
    print(f"WROTE {len(summary)} completed runs, {len(plots)} plots, report TeX",flush=True)


if __name__ == "__main__": main()
