#!/usr/bin/env python
import argparse, csv, sys
from pathlib import Path
import networkx as nx, numpy as np, pandas as pd, torch, yaml
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument("row", type=int, nargs="?"); p.add_argument("--smoke", type=Path); a=p.parse_args()
r={"architecture":"gated", "output_directory":str(a.smoke), "run_id":"smoke_gated_500"} if a.smoke else list(csv.DictReader(open(root/"manifests/master_experiment_manifest.csv")))[a.row]
if r["architecture"]!="gated": raise SystemExit(0)
out=Path(r["output_directory"]); dest=out/"gates.csv"

import scglue
model=scglue.models.load_model(out/"final.dill"); z=model.get_graph_gates(); vertices=np.asarray(model.vertices)
z={k:v.detach().cpu().numpy() if hasattr(v,"detach") else np.asarray(v) for k,v in z.items()}
assert set(z)=={"source","target","logit","gate","is_self_loop"}
eidx=np.stack([z["source"],z["target"]]); logits=z["logit"]; gates=z["gate"]; loops=np.asarray(z["is_self_loop"],dtype=bool)
# Fixed self-loops have gate=1 and deliberately undefined (NaN) logits.
assert np.isfinite(logits[~loops]).all() and np.isnan(logits[loops]).all()
assert np.isfinite(gates).all() and ((gates>=0)&(gates<=1)).all()
assert np.all(gates[loops] == 1)
assert np.allclose(gates[~loops],1/(1+np.exp(-logits[~loops])),rtol=1e-6,atol=1e-7)
df=pd.DataFrame({"source":vertices[eidx[0]],"target":vertices[eidx[1]],"logit":logits,"gate":gates,"is_self_loop":loops})
assert not df.duplicated(["source","target"]).any(); df.to_csv(dest,index=False)
x=df.loc[~df.is_self_loop,"gate"]
s={"run_id":r["run_id"],"n":len(x),"mean":x.mean(),"median":x.median(),"sd":x.std(ddof=1),"min":x.min(),"max":x.max(),"q05":x.quantile(.05),"q95":x.quantile(.95),"n_lt_0.50":int((x<.5).sum()),"pct_lt_0.50":100*(x<.5).mean(),"n_lt_0.10":int((x<.1).sum()),"pct_lt_0.10":100*(x<.1).mean()}
with open(out/"gate_summary.yaml","w") as f: yaml.safe_dump({k: v.item() if isinstance(v, np.generic) else v for k, v in s.items()},f)
