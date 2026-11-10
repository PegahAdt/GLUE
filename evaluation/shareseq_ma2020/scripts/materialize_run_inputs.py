#!/usr/bin/env python
import argparse
from pathlib import Path
import anndata as ad

p=argparse.ArgumentParser(); p.add_argument("run_dir",type=Path); p.add_argument("rna",type=Path); p.add_argument("atac",type=Path); p.add_argument("cells",type=Path); a=p.parse_args()
a.run_dir.mkdir(parents=True,exist_ok=True)
ids=[x.strip() for x in a.cells.read_text().splitlines() if x.strip()]
for source,name in ((a.rna,"rna.h5ad"),(a.atac,"atac.h5ad")):
    out=a.run_dir/name
    if out.is_file() and out.stat().st_size: continue
    x=ad.read_h5ad(source)
    if len(ids)!=len(set(ids)) or not set(ids).issubset(x.obs_names): raise RuntimeError("Invalid cell manifest")
    x=x[ids].copy(); assert list(x.obs_names)==ids
    x.write_h5ad(out,compression="gzip")

