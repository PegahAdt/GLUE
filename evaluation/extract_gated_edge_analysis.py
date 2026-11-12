#!/usr/bin/env python3
"""Extract and interpret gates from completed GATED GLUE checkpoints only.

This script never trains, encodes, or modifies a model.  It is intended to run
as a small CPU Slurm job because it loads saved checkpoints and guidance graphs.
"""

from __future__ import annotations

import argparse
import math
import re
import subprocess
from pathlib import Path

import anndata as ad
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import spearmanr

import scglue
from scglue.models.data import GraphDataset
from scglue.num import normalize_edges


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evaluation/results_gated/raw/10x-Multiome-Pbmc10k"
OUT = ROOT / "evaluation/gate_analysis"
INITIAL_GATE = 0.95
QUANTILES = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
THRESHOLDS = [0.95, 0.90, 0.75, 0.50, 0.25, 0.10]


def tex_escape(value):
    text = str(value)
    for old, new in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                     ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                     ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"),
                     ("^", r"\textasciicircum{}")]:
        text = text.replace(old, new)
    return text


def parse_path(text: str, flag: str) -> Path:
    match = re.search(rf"--{re.escape(flag)}\s+(\S+)", text)
    if not match:
        raise RuntimeError(f"Could not recover --{flag} from run_info.yaml")
    return Path(match.group(1))


def discover_models():
    found = []
    for model_path in RESULTS.glob("**/seed:0/final.dill"):
        if "fine-tune" in model_path.parts or "pretrain" in model_path.parts:
            continue
        rel = model_path.relative_to(RESULTS)
        if rel.parts[0] == "original":
            label, size, seed = "full_reference", "full", None
        else:
            m = re.fullmatch(r"subsample_size:(250|2000|8000)-subsample_seed:([012])", rel.parts[0])
            if not m:
                continue
            size, seed = int(m.group(1)), int(m.group(2))
            label = f"size{size}_seed{seed}"
        run_info = model_path.parent / "run_info.yaml"
        if not run_info.exists() or model_path.stat().st_size == 0:
            continue
        text = run_info.read_text()
        required = ["graph_encoder: gated", "gate_init: 0.95", "lam_keep: 0.0", "n_cells:", "time:"]
        if not all(token in text for token in required):
            raise RuntimeError(f"Run metadata failed validation: {run_info}")
        found.append(dict(label=label, size=size, seed=seed, model=model_path,
                          run_info=run_info, prior=parse_path(text, "prior"),
                          rna=parse_path(text, "input-rna"), atac=parse_path(text, "input-atac")))
    expected = {"full_reference"} | {f"size{s}_seed{k}" for s in (250, 2000, 8000) for k in range(3)}
    labels = {x["label"] for x in found}
    if labels != expected or len(found) != 10:
        raise RuntimeError(f"Expected exactly the 10 successful final models; found {sorted(labels)}")
    return sorted(found, key=lambda x: (x["label"] != "full_reference", str(x["label"])))


def feature_types(rna_path: Path, atac_path: Path):
    rna = ad.read_h5ad(rna_path, backed="r")
    genes = set(map(str, rna.var_names))
    rna.file.close()
    atac = ad.read_h5ad(atac_path, backed="r")
    regions = set(map(str, atac.var_names))
    atac.file.close()
    overlap = genes & regions
    if overlap:
        raise RuntimeError(f"RNA/ATAC feature identities overlap ({len(overlap)} names); types ambiguous")
    return genes, regions


def extract_one(meta):
    model = scglue.models.load_model(meta["model"])
    if getattr(model, "graph_encoder", None) != "gated":
        raise RuntimeError(f"Not a gated model: {meta['model']}")
    gate_info = model.get_graph_gates()
    required = {"source", "target", "logit", "gate", "is_self_loop"}
    if set(gate_info) != required:
        raise RuntimeError(f"Unexpected gate fields: {set(gate_info)}")
    arrays = {k: v.detach().cpu().numpy() for k, v in gate_info.items()}
    n = len(arrays["gate"])
    if any(len(v) != n for v in arrays.values()):
        raise RuntimeError("Gate arrays have inconsistent lengths")
    vertices = pd.Index(model.vertices.astype(str))
    src_i = arrays["source"].astype(np.int64)
    tgt_i = arrays["target"].astype(np.int64)
    if src_i.min() < 0 or tgt_i.min() < 0 or src_i.max() >= len(vertices) or tgt_i.max() >= len(vertices):
        raise RuntimeError("Gate source/target is not a valid model.vertices index")

    graph = nx.read_graphml(meta["prior"])
    graph_data = GraphDataset(graph, vertices, "weight", "sign", neg_samples=0,
                              weighted_sampling=False, deemphasize_loops=False)
    enorm = normalize_edges(graph_data.eidx, graph_data.ewt)
    graph_by_edge = {}
    for pos, (i, j) in enumerate(graph_data.eidx.T):
        key = (int(i), int(j))
        if key in graph_by_edge:
            raise RuntimeError(f"Duplicate directed guidance edge: {key}")
        graph_by_edge[key] = (float(graph_data.ewt[pos]), float(graph_data.esgn[pos]), float(enorm[pos]))
    configured = set(zip(src_i, tgt_i))
    if configured != set(graph_by_edge):
        raise RuntimeError("Configured gate topology differs from authoritative guidance graph")
    aligned = [graph_by_edge[(int(i), int(j))] for i, j in zip(src_i, tgt_i)]
    prior_weight, prior_sign, normalized = map(np.asarray, zip(*aligned))
    loops = arrays["is_self_loop"].astype(bool)
    if not np.array_equal(loops, src_i == tgt_i):
        raise RuntimeError("is_self_loop disagrees with directed edge identity")
    if not np.allclose(arrays["gate"][loops], 1.0):
        raise RuntimeError("Self-loop gates are not fixed at 1")
    if not np.isnan(arrays["logit"][loops]).all():
        raise RuntimeError("Expected self-loop logits to be NaN")

    genes, regions = feature_types(meta["rna"], meta["atac"])
    def ftype(x):
        return "gene" if x in genes else "region" if x in regions else "other"
    source = vertices.take(src_i).to_numpy()
    target = vertices.take(tgt_i).to_numpy()
    source_type = np.array([ftype(x) for x in source])
    target_type = np.array([ftype(x) for x in target])

    nonloop_edges = [(int(i), int(j)) for i, j, loop in zip(src_i, tgt_i, loops) if not loop]
    out_degree = pd.Series([i for i, _ in nonloop_edges]).value_counts()
    in_degree = pd.Series([j for _, j in nonloop_edges]).value_counts()
    df = pd.DataFrame({
        "source_index": src_i, "target_index": tgt_i, "source": source, "target": target,
        "logit": arrays["logit"], "gate": arrays["gate"], "is_self_loop": loops,
        "initial_gate": INITIAL_GATE, "delta_gate": arrays["gate"] - INITIAL_GATE,
        "suppression": 1 - arrays["gate"], "prior_weight": prior_weight,
        "prior_sign": prior_sign, "normalized_coefficient": normalized,
        "effective_coefficient": prior_sign * normalized * arrays["gate"],
        "absolute_effective_coefficient": np.abs(normalized * arrays["gate"]),
        "attenuation_of_original_coefficient": np.abs(normalized) * (1 - arrays["gate"]),
        "source_type": source_type, "target_type": target_type,
        "edge_type": np.char.add(np.char.add(source_type, " -> "), target_type),
        "source_degree": [int(out_degree.get(i, 0)) for i in src_i],
        "target_degree": [int(in_degree.get(j, 0)) for j in tgt_i],
    })
    df.to_csv(OUT / f"gates_{meta['label']}.csv", index=False)
    non = df.loc[~df.is_self_loop].copy()
    non.nsmallest(50, "gate").to_csv(OUT / f"lowest_gates_{meta['label']}.csv", index=False)
    non.nlargest(50, "suppression").to_csv(OUT / f"highest_suppression_{meta['label']}.csv", index=False)
    non.nlargest(50, "attenuation_of_original_coefficient").to_csv(
        OUT / f"largest_attenuations_{meta['label']}.csv", index=False)
    non.nlargest(50, "absolute_effective_coefficient").to_csv(
        OUT / f"largest_effective_coefficients_{meta['label']}.csv", index=False)
    rev = non.rename(columns={"source": "target", "target": "source", "gate": "gate_reverse"})[
        ["source", "target", "gate_reverse"]]
    pairs = non.merge(rev, on=["source", "target"], how="inner")
    pairs = pairs.loc[pairs.source < pairs.target, ["source", "target", "gate", "gate_reverse"]]
    pairs = pairs.rename(columns={"gate": "gate_A_to_B", "gate_reverse": "gate_B_to_A"})
    pairs["absolute_gate_difference"] = (pairs.gate_A_to_B - pairs.gate_B_to_A).abs()
    pairs.sort_values("absolute_gate_difference", ascending=False).to_csv(
        OUT / f"directional_asymmetry_{meta['label']}.csv", index=False)
    return df, pairs


def model_summary(label, df):
    x = df.loc[~df.is_self_loop, "gate"]
    row = {"model": label, "n_trainable_edges": len(x), "gate_min": x.min(), "gate_mean": x.mean(),
           "gate_median": x.median(), "gate_max": x.max(), "gate_sd": x.std(ddof=1)}
    row.update({f"gate_q{int(q*100):02d}": x.quantile(q) for q in QUANTILES})
    row.update({f"n_gate_lt_{t:.2f}": int((x < t).sum()) for t in THRESHOLDS})
    return row


def stability_tables(frames):
    outputs = {}
    rank_rows = []
    for size in (250, 2000, 8000):
        merged = None
        for seed in range(3):
            x = frames[f"size{size}_seed{seed}"]
            x = x.loc[~x.is_self_loop, ["source", "target", "source_type", "target_type", "edge_type", "gate"]]
            x = x.rename(columns={"gate": f"gate_seed{seed}"})
            merged = x if merged is None else merged.merge(
                x[["source", "target", f"gate_seed{seed}"]], on=["source", "target"], validate="one_to_one")
        gs = merged[[f"gate_seed{s}" for s in range(3)]]
        merged["mean_gate"] = gs.mean(axis=1)
        merged["sample_sd_gate"] = gs.std(axis=1, ddof=1)
        merged["min_gate"] = gs.min(axis=1)
        merged["max_gate"] = gs.max(axis=1)
        merged["mean_suppression"] = 1 - merged.mean_gate
        merged["stability_class"] = np.select(
            [(merged.mean_gate < 0.90) & (merged.sample_sd_gate <= merged.sample_sd_gate.quantile(.25)),
             (merged.sample_sd_gate >= merged.sample_sd_gate.quantile(.95)),
             (merged.mean_gate >= 0.95) & (merged.sample_sd_gate <= merged.sample_sd_gate.quantile(.25))],
            ["consistently_suppressed", "unstable", "consistently_retained"], default="other")
        merged.sort_values(["mean_gate", "sample_sd_gate"]).to_csv(OUT / f"gate_stability_size{size}.csv", index=False)
        for a in range(3):
            for b in range(a + 1, 3):
                rho, p = spearmanr(merged[f"gate_seed{a}"], merged[f"gate_seed{b}"])
                rank_rows.append({"size": size, "seed_a": a, "seed_b": b, "spearman_rho": rho, "p_value": p})
        outputs[size] = merged
    ranks = pd.DataFrame(rank_rows)
    ranks.to_csv(OUT / "seed_rank_correlations.csv", index=False)
    return outputs, ranks


def prior_relationship(full):
    non = full.loc[~full.is_self_loop].copy()
    rows = []
    for predictor in ["prior_weight", "normalized_coefficient", "source_degree", "target_degree"]:
        for outcome in ["gate", "suppression", "attenuation_of_original_coefficient"]:
            rho, p = spearmanr(non[predictor], non[outcome])
            rows.append({"predictor": predictor, "outcome": outcome, "spearman_rho": rho, "p_value": p,
                         "n": len(non)})
    corr = pd.DataFrame(rows)
    corr.to_csv(OUT / "full_reference_rank_correlations.csv", index=False)
    group_rows = []
    for grouping in ["prior_sign", "edge_type"]:
        for value, x in non.groupby(grouping):
            group_rows.append({"grouping": grouping, "value": value, "n": len(x),
                               "mean_gate": x.gate.mean(), "median_gate": x.gate.median(),
                               "mean_suppression": x.suppression.mean(),
                               "mean_attenuation": x.attenuation_of_original_coefficient.mean()})
    groups = pd.DataFrame(group_rows)
    groups.to_csv(OUT / "full_reference_group_summaries.csv", index=False)
    return corr, groups


def plots(frames, stability, full, pairs):
    pdir = OUT / "plots"
    pdir.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="paper")
    non = full.loc[~full.is_self_loop].copy()
    paths = []
    def save(name):
        path = pdir / name
        plt.tight_layout(); plt.savefig(path, dpi=300, bbox_inches="tight"); plt.close(); paths.append(path)
    plt.figure(figsize=(6, 4)); sns.histplot(non.gate, bins=50, kde=True); plt.xlabel("Learned gate"); save("01_full_gate_histogram.png")
    plt.figure(figsize=(6, 4)); sns.ecdfplot(data=non, x="gate"); plt.xlabel("Learned gate"); save("02_full_gate_ecdf.png")
    long = []
    for label, df in frames.items():
        size = "full" if label == "full_reference" else label.split("_")[0].replace("size", "")
        z = df.loc[~df.is_self_loop, ["gate"]].copy(); z["subset_size"] = size; long.append(z)
    long = pd.concat(long); long["subset_size"] = pd.Categorical(long.subset_size, ["250", "2000", "8000", "full"], ordered=True)
    plt.figure(figsize=(7, 4)); sns.violinplot(data=long, x="subset_size", y="gate", inner="quartile", cut=0); save("03_gate_by_subset_size.png")
    plt.figure(figsize=(7, 4)); sns.boxplot(data=non, x="edge_type", y="gate", showfliers=False); plt.xticks(rotation=25, ha="right"); save("04_gate_by_edge_type.png")
    sample = non.sample(min(30000, len(non)), random_state=0)
    plt.figure(figsize=(6, 4)); sns.scatterplot(data=sample, x="prior_weight", y="gate", hue="edge_type", s=8, alpha=.35); save("05_gate_vs_prior_weight.png")
    plt.figure(figsize=(6, 4)); sns.scatterplot(data=sample, x="normalized_coefficient", y="gate", hue="edge_type", s=8, alpha=.35); save("06_gate_vs_normalized_coefficient.png")
    stab = pd.concat([x.assign(size=str(s)) for s, x in stability.items()], ignore_index=True)
    plt.figure(figsize=(6, 4)); sns.scatterplot(data=stab.sample(min(40000, len(stab)), random_state=0), x="mean_gate", y="sample_sd_gate", hue="size", s=8, alpha=.4); save("07_gate_seed_stability.png")
    top = non.nsmallest(20, "gate").sort_values("gate", ascending=False); top["edge"] = top.source + " -> " + top.target
    plt.figure(figsize=(7, 6)); sns.barplot(data=top, x="gate", y="edge", color="#4472C4"); save("08_top20_suppressed_full.png")
    top = non.nlargest(20, "attenuation_of_original_coefficient").sort_values("attenuation_of_original_coefficient"); top["edge"] = top.source + " -> " + top.target
    plt.figure(figsize=(7, 6)); sns.barplot(data=top, x="attenuation_of_original_coefficient", y="edge", color="#C55A11"); save("09_top20_largest_attenuations.png")
    if len(pairs):
        top = pairs.nlargest(20, "absolute_gate_difference").sort_values("absolute_gate_difference"); top["pair"] = top.source + " / " + top.target
        plt.figure(figsize=(7, 6)); sns.barplot(data=top, x="absolute_gate_difference", y="pair", color="#70AD47"); save("10_directional_asymmetry.png")
    return paths


def table_tex(df, cols, n=20, formats=None):
    x = df.loc[:, cols].head(n).copy()
    formats = formats or {}
    for col, digits in formats.items():
        x[col] = x[col].map(lambda v: f"{v:.{digits}g}")
    x.columns = [tex_escape(c.replace("_", " ")) for c in x.columns]
    return x.to_latex(index=False, escape=True, longtable=False)


def write_report(models, summary, full, stability, ranks, corr, groups, plot_paths):
    non = full.loc[~full.is_self_loop]
    robust = full.loc[~full.is_self_loop].merge(
        stability[8000][["source", "target", "mean_gate", "sample_sd_gate"]], on=["source", "target"])
    robust = robust.sort_values(["mean_gate", "sample_sd_gate", "gate"])
    atten = non.nlargest(20, "attenuation_of_original_coefficient")
    retained = non.nlargest(20, "gate")
    tex = [r"\documentclass[10pt]{article}", r"\usepackage[margin=0.75in]{geometry}",
           r"\usepackage{graphicx,booktabs,float,longtable}", r"\usepackage[hidelinks]{hyperref}",
           r"\title{GATED GLUE Learned Directed-Edge Gate Interpretation}", r"\author{Post hoc analysis of saved models}",
           r"\date{\today}", r"\begin{document}", r"\maketitle",
           r"\section{Definition and interpretation}",
           r"For directed edge $i\rightarrow j$, gated propagation uses $s_{ij}\,\tilde w_{ij}\,g_{ij}$, where $s$ is the prior sign, $\tilde w$ is the exact coefficient returned by the existing GraphDataset and normalize\_edges implementation (default keepvar mode), and $g=\mathrm{sigmoid}(\ell)\in(0,1)$. A gate near 1 largely retains the original normalized contribution; a gate near 0 strongly attenuates it. The gate cannot amplify above the original normalized strength or reverse its sign. It is a global learned multiplier, not an edge-existence probability, causal effect, confidence score, p-value, or cell-specific attention score. Self-loops are fixed at gate 1 and excluded from biological rankings. With $\lambda_{keep}=0$, no explicit retention or sparsity penalty was applied.",
           r"\section{Extraction method}",
           r"Ten successful top-level \texttt{final.dill} checkpoints were selected using directory identity and \texttt{run\_info.yaml}. Intermediate pretrain/fine-tune checkpoints were excluded. \texttt{get\_graph\_gates()} supplied source/target indices, logits, gates, and loop flags. Indices were validated against \texttt{model.vertices}. Each run's exact \texttt{--prior} GraphML was read; GraphDataset generated directed identities and raw weights/signs, and \texttt{normalize\_edges} generated coefficients. All quantities were joined by directed edge identity, never raw position. Feature type came from exact RNA/ATAC var-name membership in the authoritative run inputs.",
           r"\section{Gate distributions}", table_tex(summary, ["model", "n_trainable_edges", "gate_min", "gate_mean", "gate_median", "gate_max", "gate_sd"], n=20,
                                                             formats={"gate_min":4,"gate_mean":4,"gate_median":4,"gate_max":4,"gate_sd":4}),
           r"\begin{figure}[H]\centering\includegraphics[width=.7\linewidth]{plots/01_full_gate_histogram.png}\caption{Full-reference non-self-loop gate distribution.}\end{figure}",
           r"\begin{figure}[H]\centering\includegraphics[width=.7\linewidth]{plots/02_full_gate_ecdf.png}\caption{Full-reference gate ECDF.}\end{figure}",
           r"\section{Full-reference rankings}",
           r"Lowest gate ranks strongest relative suppression/distrust. Largest attenuation ranks the largest reduction in original normalized message strength. Largest absolute effective coefficient ranks the strongest remaining gated propagation. These are distinct questions.",
           r"\subsection{Lowest gates}", table_tex(non.nsmallest(20,"gate"), ["source","target","edge_type","gate","normalized_coefficient"], formats={"gate":4,"normalized_coefficient":4}),
           r"\subsection{Largest coefficient attenuations}", table_tex(atten, ["source","target","edge_type","gate","attenuation_of_original_coefficient"], formats={"gate":4,"attenuation_of_original_coefficient":4}),
           r"\subsection{Strongest retained edges}", table_tex(retained, ["source","target","edge_type","gate","absolute_effective_coefficient"], formats={"gate":4,"absolute_effective_coefficient":4}),
           r"\section{Seed stability}", table_tex(ranks, ["size","seed_a","seed_b","spearman_rho","p_value"], n=20, formats={"spearman_rho":4,"p_value":3}),
           r"A robustly suppressed candidate should combine low mean gate with low seed variability. A single-seed extreme is not treated as robust.",
           r"\subsection{Strongest robustly suppressed edges (8000-cell stability)}", table_tex(robust, ["source","target","edge_type","gate","mean_gate","sample_sd_gate"], formats={"gate":4,"mean_gate":4,"sample_sd_gate":3}),
           r"\begin{figure}[H]\centering\includegraphics[width=.7\linewidth]{plots/07_gate_seed_stability.png}\caption{Across-seed mean gate versus sample standard deviation.}\end{figure}",
           r"\section{Edge type and prior graph relationships}",
           r"These summaries and Spearman rank correlations are descriptive associations and do not establish causality.",
           table_tex(groups, ["grouping","value","n","mean_gate","median_gate","mean_attenuation"], n=30, formats={"mean_gate":4,"median_gate":4,"mean_attenuation":4}),
           table_tex(corr, ["predictor","outcome","spearman_rho","p_value","n"], n=30, formats={"spearman_rho":4,"p_value":3}),
           r"\begin{figure}[H]\centering\includegraphics[width=.7\linewidth]{plots/04_gate_by_edge_type.png}\caption{Full-reference gate distribution by authoritative feature type.}\end{figure}",
           r"\section{Directional asymmetry}",
           r"Opposite directions are independent trainable edges. Bidirectional pairs are retained separately in the raw table and joined only for this asymmetry analysis.",
           r"\begin{figure}[H]\centering\includegraphics[width=.7\linewidth]{plots/10_directional_asymmetry.png}\caption{Most asymmetric bidirectional full-reference relationships.}\end{figure}",
           r"\section{Limitations}",
           r"Attenuation is model- and objective-dependent and does not show that an edge is biologically false. Rankings have no formal pruning threshold and require external validation. Raw prior weight and normalized propagation coefficient are distinct. Subsample models assess reproducibility but are not averaged with the primary full-data model.",
           r"\section{Model files}", r"\begin{itemize}"]
    tex.extend([r"\item \texttt{" + tex_escape(str(m["model"])) + "}" for m in models])
    tex.extend([r"\end{itemize}", r"\end{document}"])
    path = OUT / "gated_edge_interpretation.tex"
    path.write_text("\n".join(tex))
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", path.name], cwd=OUT, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", path.name], cwd=OUT, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return robust


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    models = discover_models()
    pd.DataFrame(models).to_csv(OUT / "models_used.csv", index=False)
    frames, pair_frames = {}, {}
    for meta in models:
        frames[meta["label"]], pair_frames[meta["label"]] = extract_one(meta)
    summary = pd.DataFrame([model_summary(k, v) for k, v in frames.items()])
    summary.to_csv(OUT / "gate_distribution_summary.csv", index=False)
    stability, ranks = stability_tables(frames)
    full = frames["full_reference"]
    non = full.loc[~full.is_self_loop].copy()
    non.sort_values("gate").to_csv(OUT / "full_reference_ranked_gates.csv", index=False)
    non.sort_values("attenuation_of_original_coefficient", ascending=False).to_csv(
        OUT / "full_reference_largest_attenuations.csv", index=False)
    corr, groups = prior_relationship(full)
    plot_paths = plots(frames, stability, full, pair_frames["full_reference"])
    robust = write_report(models, summary, full, stability, ranks, corr, groups, plot_paths)
    summary_main = non.merge(
        stability[250][["source","target","mean_gate","sample_sd_gate"]].rename(columns={"mean_gate":"mean_gate_size250","sample_sd_gate":"sample_sd_gate_size250"}),
        on=["source","target"], how="left").merge(
        stability[2000][["source","target","mean_gate","sample_sd_gate"]].rename(columns={"mean_gate":"mean_gate_size2000","sample_sd_gate":"sample_sd_gate_size2000"}),
        on=["source","target"], how="left").merge(
        stability[8000][["source","target","mean_gate","sample_sd_gate"]].rename(columns={"mean_gate":"mean_gate_size8000","sample_sd_gate":"sample_sd_gate_size8000"}),
        on=["source","target"], how="left")
    summary_main.to_csv(OUT / "gated_edge_summary.csv", index=False)
    robust.head(50).to_csv(OUT / "robustly_suppressed_edges.csv", index=False)
    print(f"Analysis complete: {OUT}")


if __name__ == "__main__":
    main()
