"""Check paired SHARE-seq inputs and metric outputs using the preserved cache validator."""
import argparse
from pathlib import Path
import sys

import anndata as ad
import numpy as np
import pandas as pd
import yaml

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'evaluation/shareseq_ma2020/scripts'))
from unirep_cache import validate_rep


def verify_inputs(manifest, output, dimension, representations):
    ids = manifest.read_text().splitlines()
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate cells in manifest')
    for name, representation in zip(('rna','atac'), representations):
        data = ad.read_h5ad(output/(name+'.h5ad'), backed='r')
        try:
            if list(data.obs_names) != ids:
                raise ValueError('Prepared observations do not match manifest')
            validate_rep(representation, data, ids)
        finally:
            data.file.close()
        latent = pd.read_csv(output/(name+'_latent.csv'), header=None, index_col=0)
        if list(latent.index) != ids or latent.shape != (len(ids),dimension):
            raise ValueError('Latent observations or dimension do not match manifest')
        if not np.isfinite(latent.to_numpy()).all():
            raise ValueError('Nonfinite latent values')


def verify_metrics(path):
    expected = {'mean_average_precision','normalized_mutual_info','avg_silhouette_width',
                'avg_silhouette_width_batch','graph_connectivity','foscttm',
                'neighbor_conservation','seurat_alignment_score'}
    metrics = yaml.safe_load(path.read_text())
    if set(metrics) != expected or not all(np.isfinite(value) for value in metrics.values()):
        raise ValueError('Unexpected or nonfinite SHARE integration metrics')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics', type=Path)
    parser.add_argument('inputs', nargs='*')
    args = parser.parse_args()
    if args.metrics:
        verify_metrics(args.metrics)
    else:
        manifest, output, dimension, rna, atac = args.inputs
        verify_inputs(Path(manifest), Path(output), int(dimension), [Path(rna),Path(atac)])
