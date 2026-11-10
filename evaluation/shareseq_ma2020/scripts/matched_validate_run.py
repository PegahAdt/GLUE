#!/usr/bin/env python
import argparse,csv,json
from pathlib import Path
import pandas as pd
import numpy as np
p=argparse.ArgumentParser(); p.add_argument("row",type=int); p.add_argument("--quiet",action="store_true"); a=p.parse_args()
root=Path(__file__).resolve().parents[1]; r=list(csv.DictReader(open(root/"manifests/matched_subsample_manifest.csv")))[a.row]; out=Path(r["output_directory"])
try:
    required=["final.dill","rna_latent.csv","atac_latent.csv","feature_latent.csv","run_info.yaml","requested_configuration.json"]
    assert all((out/x).is_file() and (out/x).stat().st_size for x in required)
    stamp=json.loads((out/"requested_configuration.json").read_text())
    for k in ("run_id","architecture","cell_count","replicate_source","subsample_seed","model_seed","latent_dim","gate_init","lam_keep","gat_negative_slope","graph_checksum","git_commit"): assert str(stamp[k])==str(r[k])
    n=int(r["cell_count"]); rl=pd.read_csv(out/"rna_latent.csv",header=None,index_col=0); al=pd.read_csv(out/"atac_latent.csv",header=None,index_col=0)
    assert rl.shape==(n,50) and al.shape==(n,50) and rl.index.equals(al.index)
    assert rl.index.tolist()==Path(r["cell_manifest_path"]).read_text().splitlines()
    assert np.isfinite(rl.values).all() and np.isfinite(al.values).all()
except Exception as e:
    if not a.quiet: print(f"INVALID {r['run_id']}: {e}")
    raise SystemExit(1)
if not a.quiet: print(f"VALID {r['run_id']}")
