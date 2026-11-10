"""Fail before training if ordered inputs or immutable provenance differ."""
import csv, hashlib, json, sys
from pathlib import Path
import h5py
R=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((R/'manifests/matched_subsample_manifest.csv').open()))
audit=json.loads((R/'analysis/matched_subsample_preflight.json').read_text())
for i in ([int(sys.argv[1])] if len(sys.argv)>1 else range(18)):
 r=rows[i]; a=audit['runs'][i]; p=Path(r['cell_manifest_path']); ids=p.read_text().splitlines()
 assert hashlib.sha256(p.read_bytes()).hexdigest()==a['cell_manifest_sha256']
 assert hashlib.sha256(Path(r['graph_path']).read_bytes()).hexdigest()==r['graph_checksum']
 g=R/'results'/a['gated_run_id']
 for modality in ('rna','atac'):
  for path in (g/f'{modality}.h5ad',Path(r['output_directory'])/f'{modality}.h5ad'):
   if not path.exists():
    assert len(sys.argv)==1 and path.parent!=g, path
    continue
   with h5py.File(path) as f:
    obs=f['obs']; observed=obs[obs.attrs['_index']].asstr()[:].tolist()
    assert observed==ids, path
 print('PAIRED',r['run_id'],len(ids))
