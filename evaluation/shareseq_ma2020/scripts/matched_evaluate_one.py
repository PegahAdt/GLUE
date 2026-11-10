#!/usr/bin/env python
"""Evaluate saved GLUE latents using cached canonical subset PCA/LSI."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
import yaml
from unirep_cache import ROOT, REPO, ensure_unireps

p = argparse.ArgumentParser()
p.add_argument('row', type=int, nargs='?')
p.add_argument('--smoke', type=Path)
a = p.parse_args()
if a.smoke:
    out = a.smoke
    manifest = ROOT / 'manifests/cells_smoke500_seed0.txt'
else:
    with (ROOT / 'manifests/matched_subsample_manifest.csv').open() as f:
        row = list(csv.DictReader(f))[a.row]
    out = Path(row['output_directory'])
    manifest = Path(row['cell_manifest_path'])
ids = manifest.read_text().splitlines()
assert len(ids) == len(set(ids))
latents = [pd.read_csv(out / f'{m}_latent.csv', header=None, index_col=0) for m in ('rna', 'atac')]
for latent in latents:
    assert list(latent.index) == ids, 'Latent/manifest observation order mismatch'
    assert latent.shape == (len(ids), 50)
    assert np.isfinite(latent.to_numpy()).all()
assert latents[0].index.equals(latents[1].index), 'Paired FOSCTTM order mismatch'
run_env = os.environ.copy()
run_env.update(PYTHONPATH=str(REPO), PYTHONNOUSERSITE='1', PATH=str(REPO / 'conda/bin') + os.pathsep + run_env.get('PATH', ''))
# Reuse the exact cache already recorded by the matched GATED evaluation.
from unirep_cache import validate_rep
import anndata as ad
gated = ROOT / 'results' / f"gated_size{row['cell_count']}_subsample{row['subsample_seed']}_model0_gate0.95"
record = json.loads((gated / 'unirep_inputs.json').read_text())
paths = [Path(record[m]) for m in ('rna', 'atac')]
for modality, path in zip(('rna', 'atac'), paths):
    dataset = ad.read_h5ad(out / f'{modality}.h5ad', backed='r')
    try:
        assert list(dataset.obs_names) == ids
        validate_rep(path, dataset, ids)
    finally:
        dataset.file.close()
dest = out / 'cell_integration.yaml'
# Always execute: an old nonempty YAML is not proof of evaluation with this cache.
temporary = out / 'cell_integration.tmp.yaml'
cmd = [str(REPO / 'conda/bin/python'), str(REPO / 'evaluation/workflow/scripts/cell_integration.py'),
       '-d', *map(str, paths), '-l', str(out / 'rna_latent.csv'), str(out / 'atac_latent.csv'),
       '--cell-type', 'cell_type', '--domain', 'domain', '--paired', '-o', str(temporary)]
subprocess.run(cmd, check=True, env=run_env)
metrics = yaml.safe_load(temporary.read_text())
expected = {'mean_average_precision', 'normalized_mutual_info', 'avg_silhouette_width', 'graph_connectivity',
            'seurat_alignment_score', 'avg_silhouette_width_batch', 'neighbor_conservation', 'foscttm'}
assert set(metrics) == expected and all(np.isfinite(v) for v in metrics.values())
os.replace(temporary, dest)
(out / 'unirep_inputs.json').write_text(json.dumps(dict(zip(('rna', 'atac'), map(str, paths))), indent=2) + '\n')
print(f'Validated metrics with RNA/ATAC unireps: {(len(ids), 50)}; {paths}')
