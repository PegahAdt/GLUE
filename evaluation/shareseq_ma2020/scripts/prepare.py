#!/usr/bin/env python
"""Inspect, pair, prepare, graph, subsample, and manifest Ma-2020 SHARE-seq."""
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import anndata as ad
import networkx as nx
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
os.environ["PATH"] = str(REPO / "conda/bin") + os.pathsep + os.environ.get("PATH", "")
DATA = ROOT / "data"
MAN = ROOT / "manifests"
ANA = ROOT / "analysis"
SOURCE_RNA = REPO / "data/dataset/Ma-2020-RNA.h5ad"
SOURCE_ATAC = REPO / "data/dataset/Ma-2020-ATAC.h5ad"
RNA = DATA / "rna_prepared.h5ad"
ATAC = DATA / "atac_prepared.h5ad"
GRAPH = DATA / "guidance.graphml.gz"
GIT = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()

def sparse_integer_status(x):
    from scipy import sparse
    vals = x.data if sparse.issparse(x) else np.asarray(x).ravel()
    if vals.size == 0:
        return True
    sample = vals[:min(vals.size, 100000)]
    return bool(np.isfinite(sample).all() and np.allclose(sample, np.round(sample)))

def inventory_one(a, path):
    return {
        "path": str(path.resolve()), "shape": [int(a.n_obs), int(a.n_vars)],
        "obs_columns": list(a.obs.columns), "var_columns": list(a.var.columns),
        "obsm_keys": list(a.obsm.keys()), "layers_keys": list(a.layers.keys()),
        "has_raw": a.raw is not None, "X_looks_like_counts": sparse_integer_status(a.X),
        "has_pca": "X_pca" in a.obsm, "has_lsi": "X_lsi" in a.obsm,
        "has_hvg": "highly_variable" in a.var,
        "coordinate_columns": [x for x in ("chrom", "chromStart", "chromEnd", "strand") if x in a.var],
        "file_size_bytes": path.stat().st_size, "sha256": sha256(path)
    }

def completed_preparation_valid():
    return all(p.is_file() and p.stat().st_size for p in (RNA, ATAC, GRAPH, ANA / "dataset_inventory.yaml", MAN / "master_experiment_manifest.csv"))

def main():
    for d in (DATA, MAN, ANA, ROOT / "results", ROOT / "metrics", ROOT / "reports", ROOT / "logs"):
        d.mkdir(parents=True, exist_ok=True)
    if not SOURCE_RNA.is_file() or not SOURCE_ATAC.is_file():
        raise FileNotFoundError("Authoritative processed Ma-2020 files are unavailable; training is stopped")
    src_rna = ad.read_h5ad(SOURCE_RNA)
    src_atac = ad.read_h5ad(SOURCE_ATAC)
    common = src_rna.obs_names[src_rna.obs_names.isin(src_atac.obs_names)]
    if not len(common):
        raise RuntimeError("RNA/ATAC pairing cannot be established: zero cell-ID overlap")
    rna = src_rna[common].copy()
    atac = src_atac[common].copy()
    if not rna.obs_names.equals(atac.obs_names):
        atac = atac[rna.obs_names].copy()
    assert rna.obs_names.equals(atac.obs_names) and rna.obs_names.is_unique
    cell_type_candidates = [x for x in ("cell_type", "celltype", "CellType", "annotation") if x in rna.obs and x in atac.obs]
    if not cell_type_candidates:
        raise RuntimeError("No shared cell-type annotation column found")
    cell_type = cell_type_candidates[0]
    rna.obs["domain"] = "RNA"
    atac.obs["domain"] = "ATAC"
    if not RNA.exists(): rna.write_h5ad(RNA, compression="gzip")
    if not ATAC.exists(): atac.write_h5ad(ATAC, compression="gzip")
    if not GRAPH.exists():
        import itertools, scglue
        graph = scglue.genomics.rna_anchored_prior_graph(
            rna, atac, gene_region="combined", extend_range=0,
            propagate_highly_variable=True, corrupt_rate=0.0, random_state=0)
        nodes = set(itertools.chain(rna.var.query("highly_variable").index,
                                    atac.var.query("highly_variable").index))
        nx.write_graphml(graph.subgraph(nodes), GRAPH)
    graph = nx.read_graphml(GRAPH)
    for _, _, x in graph.edges(data=True):
        if "weight" not in x or "sign" not in x or not np.isfinite(float(x["weight"])) or not np.isfinite(float(x["sign"])):
            raise RuntimeError("Guidance graph has missing/nonfinite weight or sign")
    rset, aset = set(rna.var_names), set(atac.var_names)
    loops = sum(u == v for u, v in graph.edges())
    pos = sum(float(x["sign"]) > 0 for _,_,x in graph.edges(data=True))
    neg = sum(float(x["sign"]) < 0 for _,_,x in graph.edges(data=True))
    g2r = sum(u in rset and v in aset and u != v for u,v in graph.edges())
    r2g = sum(u in aset and v in rset and u != v for u,v in graph.edges())
    graph_info = {"path": str(GRAPH.resolve()), "sha256": sha256(GRAPH),
                  "nodes": graph.number_of_nodes(), "directed_edges": graph.number_of_edges(),
                  "trainable_non_self_loop_edges": graph.number_of_edges()-loops,
                  "self_loops": loops, "positive_sign_edges": pos, "negative_sign_edges": neg,
                  "gene_to_region": g2r, "region_to_gene": r2g,
                  "directed": graph.is_directed(), "same_graph_for_all_runs": True}
    inv = {"dataset": "Ma-2020 SHARE-seq mouse skin", "rna": inventory_one(src_rna, SOURCE_RNA),
           "atac": inventory_one(src_atac, SOURCE_ATAC), "rna_atac_cell_id_overlap": int(len(common)),
           "source_cell_order_identical": src_rna.obs_names.equals(src_atac.obs_names),
           "prepared_cell_order_identical": True, "cell_type_annotation": cell_type,
           "pairing_used_for_training": False, "pairing_retained_for_evaluation": True,
           "preprocessing": "Source counts, HVG flags, annotations, and coordinates preserved; only shared-ID reorder and domain labels added. Existing run_GLUE computes matched PCA/LSI in memory.",
           "guidance_graph": graph_info}
    with open(ANA / "dataset_inventory.yaml", "w") as f: yaml.safe_dump(inv, f, sort_keys=False)
    with open(ANA / "dataset_inventory.txt", "w") as f:
        f.write(yaml.safe_dump(inv, sort_keys=False))
    ids = np.asarray(rna.obs_names, dtype=str)
    for seed in (0,1,2):
        order = np.random.RandomState(seed).permutation(len(ids))
        for size in (8000,16000,24000):
            if size > len(ids): raise RuntimeError(f"Requested {size} exceeds {len(ids)} matched cells")
            np.savetxt(MAN / f"cells_size{size}_seed{seed}.txt", ids[order[:size]], fmt="%s")
    np.savetxt(MAN / "cells_sizefull.txt", ids, fmt="%s")
    (MAN / "subsampling.yaml").write_text(yaml.safe_dump({"nested_within_seed": True, "subsample_sizes": [8000,16000,24000], "subsample_seeds": [0,1,2], "full_dataset_manifest": "cells_sizefull.txt", "full_dataset_has_no_subsample_seed": True}))
    hp = {"lr":.002,"lam_graph":.02,"lam_align":.05,"dim":50,"alt_dim":100,"hidden_depth":2,
          "hidden_dim":256,"dropout":.2,"neg_samples":10,"model_seed":0,"gat_negative_slope":.2,"lam_keep":0.0}
    (MAN / "hyperparameters.yaml").write_text(yaml.safe_dump(hp, sort_keys=False))
    fields = ["run_id","dataset","architecture","cell_count","cell_label","replicate_source","subsample_seed","model_seed","latent_dim","gate_init","lam_keep","gat_negative_slope","graph_path","graph_checksum","rna_path","atac_path","cell_manifest_path","output_directory","expected_checkpoint","training_state","metric_state","gate_analysis_state","slurm_job_id","runtime","git_commit"]
    configs = []
    def add(arch,size,label,subseed,model_seed,gate=""):
        replicate_source = "cell_subsampling" if label != "full" else ("model_initialization" if arch == "gated" else "primary_architecture")
        rid = f"{arch}_size{label}" + (f"_subsample{subseed}" if subseed != "" else "") + f"_model{model_seed}" + (f"_gate{float(gate):.2f}" if gate != "" else "")
        out = ROOT / "results" / rid
        cells = MAN / (f"cells_size{label}_seed{subseed}.txt" if subseed != "" else "cells_sizefull.txt")
        configs.append(dict(run_id=rid,dataset="Ma-2020",architecture=arch,cell_count=size,cell_label=label,replicate_source=replicate_source,subsample_seed=subseed,model_seed=model_seed,latent_dim=50,gate_init=gate,lam_keep=0.0 if arch=="gated" else "",gat_negative_slope=.2 if arch=="gat" else "",graph_path=str(GRAPH.resolve()),graph_checksum=graph_info["sha256"],rna_path=str(RNA.resolve()),atac_path=str(ATAC.resolve()),cell_manifest_path=str(cells.resolve()),output_directory=str(out.resolve()),expected_checkpoint=str((out/"final.dill").resolve()),training_state="pending",metric_state="pending",gate_analysis_state="pending" if arch=="gated" else "not_applicable",slurm_job_id="",runtime="",git_commit=GIT))
    n=len(ids)
    add("gcn",n,"full","",0); add("gat",n,"full","",0)
    for size in (8000,16000,24000):
        for seed in (0,1,2): add("gated",size,str(size),seed,0,.95)
    for gate in (.50,.70,.90,.95,.99):
        for model_seed in (0,1,2): add("gated",n,"full","",model_seed,gate)
    assert len(configs)==26 and len({x["run_id"] for x in configs})==26
    with open(MAN / "master_experiment_manifest.csv", "w", newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(configs)
    with open(MAN / "provenance.json", "w") as f:
        json.dump({"sources": {"rna": inv["rna"], "atac": inv["atac"]}, "graph": graph_info,
                   "git_commit": GIT, "validated_gated_commit": "26946eb591c10c2562d96519eb654ce589f5f990"},f,indent=2)
    print(yaml.safe_dump({"rna_shape":inv["rna"]["shape"],"atac_shape":inv["atac"]["shape"],"matched_cells":len(common),"cell_type":cell_type,"graph":graph_info,"configurations":len(configs)},sort_keys=False))

if __name__ == "__main__": main()
