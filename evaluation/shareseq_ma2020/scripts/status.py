#!/usr/bin/env python
import csv,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]; rows=list(csv.DictReader(open(root/"manifests/master_experiment_manifest.csv")))
counts={"completed":0,"training_or_pending":0,"metrics_complete":0,"missing_outputs":0}
for i,r in enumerate(rows):
 out=Path(r["output_directory"]); trained=all((out/x).is_file() and (out/x).stat().st_size for x in ("final.dill","rna_latent.csv","atac_latent.csv","feature_latent.csv","run_info.yaml","requested_configuration.json")); metric=(out/"cell_integration.yaml").is_file() and (out/"cell_integration.yaml").stat().st_size
 state="complete" if trained and metric else "trained_metrics_pending" if trained else "pending_or_running"
 counts["completed"]+=state=="complete"; counts["training_or_pending"]+=not trained; counts["metrics_complete"]+=bool(metric); counts["missing_outputs"]+=not trained
 print(f"{i:02d} {state:24s} {r['run_id']} job={r['slurm_job_id'] or '-'}")
print(json.dumps(counts,indent=2))
