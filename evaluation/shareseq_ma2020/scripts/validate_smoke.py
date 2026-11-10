#!/usr/bin/env python
"""Validate completed training artifacts without retraining or changing the model."""
from pathlib import Path
import anndata as ad
import numpy as np
import pandas as pd
import scglue
import yaml
import torch

root = Path(__file__).resolve().parents[1]
out = root / 'results/smoke_gated_500'
for name in ('final.dill', 'rna_latent.csv', 'atac_latent.csv', 'feature_latent.csv', 'run_info.yaml', 'gate_diagnostics.yaml'):
    assert (out / name).stat().st_size > 0, name
ids = (root / 'manifests/cells_smoke500_seed0.txt').read_text().splitlines()
assert len(ids) == len(set(ids)) == 500
for modality in ('rna', 'atac'):
    data = ad.read_h5ad(out / f'{modality}.h5ad', backed='r')
    latent = pd.read_csv(out / f'{modality}_latent.csv', header=None, index_col=0)
    assert list(data.obs_names) == list(latent.index) == ids
    assert latent.shape == (500, 50) and np.isfinite(latent.to_numpy()).all()
    data.file.close()
model = scglue.models.load_model(out / 'final.dill')
assert all(torch.isfinite(parameter).all().item() for parameter in model.net.parameters())
features = pd.read_csv(out / 'feature_latent.csv', header=None, index_col=0)
assert list(features.index) == list(model.vertices)
assert features.shape == (len(model.vertices), 50) and np.isfinite(features.to_numpy()).all()
gates = model.get_graph_gates()
assert np.isfinite(gates['gate'].detach().cpu().numpy()).all()
diagnostics = yaml.safe_load((out / 'gate_diagnostics.yaml').read_text())
assert all(np.isfinite(v) for v in diagnostics.values())
print(f'VALID completed smoke training: RNA/ATAC (500, 50), features {features.shape}; final model loaded')
