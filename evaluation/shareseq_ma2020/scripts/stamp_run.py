#!/usr/bin/env python
import csv,json,sys,time,yaml
from pathlib import Path
root=Path(__file__).resolve().parents[1]; row=list(csv.DictReader(open(root/"manifests/master_experiment_manifest.csv")))[int(sys.argv[1])]
out=Path(row["output_directory"]); info=yaml.unsafe_load(open(out/"run_info.yaml"))
stamp={k:row[k] for k in ("run_id","architecture","cell_count","replicate_source","subsample_seed","model_seed","latent_dim","gate_init","lam_keep","gat_negative_slope","graph_checksum","git_commit")}
stamp["runtime"]=float(info.get("time",0)); stamp["completed_at_unix"]=time.time()
(out/"requested_configuration.json").write_text(json.dumps(stamp,indent=2))
