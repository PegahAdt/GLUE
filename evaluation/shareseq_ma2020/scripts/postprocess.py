#!/usr/bin/env python
"""Collect metrics/gates, stability, sensitivity tables, figures, report, validation."""
import csv, itertools, json, subprocess
from pathlib import Path
import numpy as np, pandas as pd, yaml
from scipy.stats import spearmanr
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1]; man=root/"manifests/master_experiment_manifest.csv"; rows=pd.read_csv(man,keep_default_na=False)
metric_rows=[]; gate_rows=[]
for _,r in rows.iterrows():
    out=Path(r.output_directory)
    if (out/"cell_integration.yaml").is_file():
        m=yaml.safe_load((out/"cell_integration.yaml").read_text()) or {}; m.update({k:r[k] for k in ("run_id","architecture","cell_count","cell_label","replicate_source","subsample_seed","model_seed","gate_init")});
        if (out/"run_info.yaml").is_file(): m["runtime"]=float((yaml.unsafe_load((out/"run_info.yaml").read_text()) or {}).get("time",np.nan))
        metric_rows.append(m)
    if (out/"gate_summary.yaml").is_file():
        g=yaml.safe_load((out/"gate_summary.yaml").read_text()); g.update({k:r[k] for k in ("architecture","cell_count","cell_label","replicate_source","subsample_seed","model_seed","gate_init")}); gate_rows.append(g)
metrics=pd.DataFrame(metric_rows); gates=pd.DataFrame(gate_rows); (root/"metrics").mkdir(exist_ok=True); (root/"analysis").mkdir(exist_ok=True)
metrics.to_csv(root/"metrics/full_architecture_metrics_by_run.csv",index=False)
metrics.query("cell_label == 'full' and model_seed == 0 and ((architecture != 'gated') or gate_init == '0.95')").to_csv(root/"metrics/full_architecture_comparison.csv",index=False)
gi=metrics.query("architecture == 'gated' and cell_label == 'full'").copy(); gi.to_csv(root/"metrics/gate_init_metrics_by_run.csv",index=False)
num=[c for c in gi.columns if c not in {"run_id","architecture","cell_label"} and pd.api.types.is_numeric_dtype(gi[c])]
if len(gi): gi.groupby("gate_init")[num].agg(["mean","std"]).to_csv(root/"metrics/gate_init_metrics_summary.csv")
full_gates=gates.query("cell_label == 'full'").copy() if len(gates) else gates
full_gates.to_csv(root/"analysis/shareseq_gate_init_gate_distributions_by_run.csv",index=False)
if len(full_gates): full_gates.groupby("gate_init").agg({c:["mean","std"] for c in ["mean","median","sd","min","max","q05","q95","pct_lt_0.50","pct_lt_0.10"]}).to_csv(root/"analysis/shareseq_gate_init_gate_distributions_summary.csv")
stab=[]
for size in (8000,16000,24000):
    frames=[]
    for seed in (0,1,2):
        q=rows.query("architecture == 'gated' and cell_count == @size and subsample_seed == @seed and gate_init == '0.95'")
        if len(q): frames.append((seed,pd.read_csv(Path(q.iloc[0].output_directory)/"gates.csv").query("not is_self_loop")))
    for (sa,a),(sb,b) in itertools.combinations(frames,2):
        x=a.merge(b,on=["source","target"],suffixes=("_a","_b"),validate="one_to_one"); rho=spearmanr(x.gate_a,x.gate_b).correlation; stab.append({"size":size,"seed_a":sa,"seed_b":sb,"spearman_rho":rho,"n_matched_edges":len(x)})
pd.DataFrame(stab).to_csv(root/"analysis/gate_stability_by_size.csv",index=False)
if stab:
    s=pd.DataFrame(stab); z=s.groupby("size").spearman_rho.agg(["mean","std"]).reset_index(); z.to_csv(root/"analysis/gate_stability_by_size_summary.csv",index=False); plt.figure(figsize=(5,4)); plt.errorbar(z["size"],z["mean"],yerr=z["std"],marker="o"); plt.xlabel("Matched cells"); plt.ylabel("Pairwise Spearman rho"); plt.tight_layout(); plt.savefig(root/"analysis/gate_rank_stability_vs_dataset_size.png",dpi=300); plt.close()
if len(full_gates):
    plt.figure(figsize=(5,4)); x=full_gates.groupby("gate_init")["mean"].agg(["mean","std"]).reset_index(); plt.errorbar(x.gate_init,x["mean"],yerr=x["std"],marker="o"); plt.xlabel("Gate initialization"); plt.ylabel("Final mean gate"); plt.tight_layout(); plt.savefig(root/"analysis/final_gate_mean_vs_initialization.png",dpi=300); plt.close()
merged=gi.merge(full_gates,on="run_id",validate="one_to_one",suffixes=("_metric","_gate")) if len(gi) and len(full_gates) else pd.DataFrame(); merged.to_csv(root/"analysis/gate_metrics_merged.csv",index=False)
if len(gi):
    reference=gi.query("gate_init == '0.95'").set_index("model_seed")
    delta=[]
    for _,r in gi.iterrows():
        if r.model_seed not in reference.index: continue
        z={"run_id":r.run_id,"gate_init":r.gate_init,"model_seed":r.model_seed}
        for c in num:
            if c in reference: z[c+"_delta_vs_095"]=r[c]-reference.loc[r.model_seed,c]
        delta.append(z)
    pd.DataFrame(delta).to_csv(root/"metrics/gate_init_metric_paired_differences_vs_095.csv",index=False)
corr=[]
for gx in ("mean","median","pct_lt_0.50","pct_lt_0.10"):
    for mx in [c for c in merged.columns if c in num]:
        z=merged[[gx,mx]].dropna();
        if len(z)>=3: corr.append({"gate_statistic":gx,"metric":mx,"spearman_rho":spearmanr(z[gx],z[mx]).correlation,"n_runs":len(z)})
pd.DataFrame(corr).to_csv(root/"analysis/gate_metric_associations.csv",index=False)
validation={"requested_runs":len(rows),"completed_runs":len(metrics),"missing_runs":sorted(set(rows.run_id)-set(metrics.run_id) if len(metrics) else set(rows.run_id)),"duplicate_configurations":int(rows.run_id.duplicated().sum()),"finite_metrics":bool(np.isfinite(metrics.select_dtypes('number')).all().all()) if len(metrics) else False,"all_outputs_complete":len(metrics)==len(rows),"metric_joins_one_to_one":not merged.run_id.duplicated().any() if len(merged) else False,"graph_checksums_unique":int(rows.graph_checksum.nunique()),"notes":"8k/16k/24k replication is by paired-cell subsample_seed with model_seed=0. Full-data gate-init replication is by model_seed on one identical full cell manifest; the full model_seed=0 gate_init=0.95 run is also the architecture and size-reference endpoint."}
(root/"analysis/validation_summary.yaml").write_text(yaml.safe_dump(validation,sort_keys=False))
report=root/"reports/shareseq_gcn_gat_gated_gate_sensitivity_report.md"; report.write_text("# SHARE-seq GCN/GAT/GATED and gate sensitivity report\n\nGenerated only from the machine-readable tables in this workspace.\n\n## Dataset\n\nSee `../analysis/dataset_inventory.yaml`.\n\n## Experiment design\n\nSee `../manifests/master_experiment_manifest.csv` and `../manifests/hyperparameters.yaml`.\n\n## Results\n\nCompleted runs: %d/%d. Tables and figures are under `../metrics` and `../analysis`.\n\n## Limitations\n\nGate/metric associations are descriptive at the run level, not causal; three seeds do not support strong significance claims. Low gates do not establish that biological prior edges are invalid.\n"%(len(metrics),len(rows)))
from matplotlib.backends.backend_pdf import PdfPages
with PdfPages(root/"reports/shareseq_gcn_gat_gated_gate_sensitivity_report.pdf") as pdf:
    fig=plt.figure(figsize=(8.5,11)); fig.text(.08,.94,"SHARE-seq GCN/GAT/GATED and gate sensitivity",fontsize=17,weight="bold"); fig.text(.08,.88,f"Completed runs: {len(metrics)}/{len(rows)}\nMatched cells: {int(rows.cell_count.max())}\nSee machine-readable analysis and metrics tables for all reported values.",fontsize=11,va="top"); fig.text(.08,.72,"Sections\n1. Dataset and pairing\n2. Experiment design\n3. Full architecture comparison\n4. Learned gates\n5. Stability vs size\n6. Gate-init sensitivity\n7. Performance sensitivity\n8. Gate/performance relationships\n9. PBMC comparison\n10. Conclusions and limitations",fontsize=11,va="top"); plt.axis("off"); pdf.savefig(fig); plt.close(fig)
    for image in sorted((root/"analysis").glob("*.png")):
        fig=plt.figure(figsize=(8.5,6)); im=plt.imread(image); plt.imshow(im); plt.axis("off"); plt.title(image.stem.replace("_"," ")); pdf.savefig(fig,bbox_inches="tight"); plt.close(fig)
