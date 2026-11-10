#!/usr/bin/env python
import csv,sys,yaml
from pathlib import Path
root=Path(__file__).resolve().parents[1]; p=root/"manifests/master_experiment_manifest.csv"; rows=list(csv.DictReader(open(p))); fields=list(rows[0])
for r in rows: r["slurm_job_id"]=sys.argv[2]
with open(p,"w",newline="") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
(root/"manifests/submitted_jobs.yaml").write_text(yaml.safe_dump(dict(smoke=sys.argv[1] or "reused",training=sys.argv[2],metrics=sys.argv[3],report=sys.argv[4])))

