"""Canonical subset-level PCA/LSI cache, shared across model configurations."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess

import anndata as ad
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def validate_rep(path, dataset, ids):
    rep = ad.read_h5ad(path)
    assert list(rep.obs_names) == ids, f"Observation order mismatch: {path}"
    assert isinstance(rep.X, np.ndarray) and rep.X.ndim == 2
    assert rep.X.shape == (len(ids), 50), (path, rep.X.shape)
    assert np.isfinite(rep.X).all(), f"Nonfinite representation: {path}"
    pd.testing.assert_frame_equal(rep.obs, dataset.obs)
    return rep


def ensure_unireps(out, ids, run_env):
    sources = [ROOT / 'data' / f'{m}_prepared.h5ad' for m in ('rna', 'atac')]
    provenance = {'cells': ids, 'sources': [(str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in sources],
                  'scripts': {m: hashlib.sha256((REPO / f'evaluation/workflow/scripts/{m}_unirep.py').read_bytes()).hexdigest() for m in ('rna', 'atac')}, 'dim': 50}
    key = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
    cache = ROOT / 'data/unirep_cache' / key
    cache.mkdir(parents=True, exist_ok=True)
    paths = []
    with (cache / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for modality in ('rna', 'atac'):
            dataset = ad.read_h5ad(out / f'{modality}.h5ad', backed='r')
            try:
                assert list(dataset.obs_names) == ids, f'{modality} dataset/manifest order mismatch'
                dest = cache / f'{modality}_unirep.h5ad'
                if not dest.exists():
                    temporary = cache / f'{modality}_unirep.tmp.h5ad'
                    cmd = [str(REPO / 'conda/bin/python'), str(REPO / f'evaluation/workflow/scripts/{modality}_unirep.py'),
                           '-i', str(out / f'{modality}.h5ad'), '-d', '50', '-o', str(temporary)]
                    with (cache / f'{modality}_unirep.log').open('w') as log:
                        subprocess.run(cmd, check=True, env=run_env, stdout=log, stderr=subprocess.STDOUT)
                    validate_rep(temporary, dataset, ids)
                    os.replace(temporary, dest)
                validate_rep(dest, dataset, ids)
                paths.append(dest)
            finally:
                dataset.file.close()
        (cache / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return paths
