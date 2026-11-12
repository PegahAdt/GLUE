#!/usr/bin/env python
"""Read-only, CPU evaluation of the PBMC graph perturbation experiment.

Run --help for commands. Training outputs are never written. Scientific
definitions and departures from the legacy evaluator are in methodology.md.
"""
import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
import yaml
from scipy.spatial.distance import cdist
from scipy.stats import chi2, ks_2samp
from sklearn import metrics as skm
from sklearn import config_context
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evaluation/workflow/scripts'))
EXPERIMENT = ROOT / 'evaluation/pbmc_graph_perturbation'
INPUT = Path('/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/results_gcn_h100/raw/10x-Multiome-Pbmc10k/original')
CONDITIONS = ['original', 'retain_75', 'retain_50', 'retain_25', 'retain_10', 'randomized']


class MetadataLoader(yaml.SafeLoader):
    """Accept only the pathlib tag emitted by this project's run_info writer."""


MetadataLoader.add_constructor(
    'tag:yaml.org,2002:python/object/apply:pathlib.PosixPath',
    lambda loader, node: str(Path(*loader.construct_sequence(node)))
)


def read_info(path):
    with Path(path).open() as f:
        return yaml.load(f, Loader=MetadataLoader)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False))
    tmp.replace(path)


def read_embedding(path, ids=None, dim=None):
    frame = pd.read_csv(path, header=None, index_col=0)
    frame.index = frame.index.astype(str)
    if not frame.index.is_unique or frame.index.hasnans or frame.empty:
        raise ValueError('Empty/duplicate/missing embedding identifiers: {}'.format(path))
    x = frame.to_numpy(dtype=np.float64)
    if not np.isfinite(x).all() or (dim is not None and x.shape[1] != dim):
        raise ValueError('Nonfinite values or wrong latent dimension: {}'.format(path))
    if ids is not None:
        ids = pd.Index(ids).astype(str)
        if not ids.is_unique or set(ids) != set(frame.index):
            raise ValueError('Embedding/source identifier sets differ: {}'.format(path))
        frame = frame.loc[ids]  # Align by ID, never by assumed row order.
    return frame


def read_obs(path):
    import anndata as ad
    data = ad.read_h5ad(path, backed='r')
    try:
        obs = data.obs.copy()
        obs.index = obs.index.astype(str)
        if not obs.index.is_unique or obs.index.hasnans:
            raise ValueError('Source cell identifiers must be unique and nonmissing')
        return obs
    finally:
        data.file.close()


def verify_pairs(rna, atac, provenance):
    """Require source provenance, exact barcode sets, protocol and sample agreement."""
    evidence = {'verified': False, 'source': str(provenance)}
    if not provenance.is_file():
        evidence['reason'] = 'Source collection notebook is unavailable'
        return evidence
    notebook = json.loads(provenance.read_text())
    code = '\n'.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type'] == 'code')
    required = [
        'pbmc_granulocyte_sorted_10k_filtered_feature_bc_matrix.h5',
        'rna = adata[:, adata.var["feature_types"] == "Gene Expression"].copy()',
        'atac = adata[:, adata.var["feature_types"] == "Peaks"].copy()',
        'rna = rna[meta.index, :]', 'atac = atac[meta.index, :]',
        'rna = rna[mask, :]', 'atac = atac[mask, :]'
    ]
    if not all(item in code for item in required):
        evidence['reason'] = 'Notebook does not document the supported shared-matrix/filter provenance'
        return evidence
    if set(rna.index) != set(atac.index):
        evidence['reason'] = 'Source barcode sets differ; no partial pairing is inferred'
        return evidence
    atac = atac.loc[rna.index]
    for key, expected in [('protocol', '10x Multiome'), ('dataset', '10x-Multiome-Pbmc10k')]:
        if key not in rna or key not in atac:
            evidence['reason'] = 'Missing source {}'.format(key)
            return evidence
        if not (rna[key].astype(str).str.startswith(expected).all() and
                atac[key].astype(str).str.startswith(expected).all()):
            evidence['reason'] = 'Unexpected source {}'.format(key)
            return evidence
    if 'orig.ident' not in rna or 'orig.ident' not in atac or not np.array_equal(
            rna['orig.ident'].astype(str), atac['orig.ident'].astype(str)):
        evidence['reason'] = 'Missing or inconsistent source sample identifier'
        return evidence
    evidence.update(verified=True, n_pairs=len(rna), provenance_sha256=sha256(provenance),
                    reason='Shared source Multiome matrix and common filters; exact unique barcodes, protocol and sample identifiers verified; embeddings realigned by ID')
    return evidence


def paired_scores(x, y, chunk_size=256):
    """Exact bidirectional FOSCTTM, denominator N as in scglue.metrics.foscttm."""
    if x.shape != y.shape:
        raise ValueError('Paired arrays must have the same shape')
    n = len(x)
    counts = [0, 0]
    recalls = {}
    for direction, (a, b) in enumerate([(x, y), (y, x)]):
        hits = {k: 0 for k in [1, 5, 10]}
        for start in range(0, n, chunk_size):
            stop = min(start + chunk_size, n)
            distances = cdist(a[start:stop], b, metric='euclidean')
            true = distances[np.arange(stop-start), np.arange(start, stop)]
            counts[direction] += int((distances < true[:, None]).sum())
            # Stable tie break is target index; ties never counted as closer in FOSCTTM.
            top = np.argsort(distances, axis=1, kind='stable')[:, :min(10, n)]
            for k in hits:
                hits[k] += int((top[:, :min(k, n)] == np.arange(start, stop)[:, None]).any(axis=1).sum())
        name = ['rna_to_atac', 'atac_to_rna'][direction]
        recalls.update({'matching_recall_{}_at_{}'.format(name, k): hits[k] / n for k in hits})
    recalls['foscttm_rna_to_atac'] = counts[0] / (n*n)
    recalls['foscttm_atac_to_rna'] = counts[1] / (n*n)
    recalls['foscttm'] = sum(counts) / (2*n*n)
    for k in [1, 5, 10]:
        recalls['matching_recall_at_{}'.format(k)] = np.mean([
            recalls['matching_recall_{}_at_{}'.format(d, k)] for d in ['rna_to_atac', 'atac_to_rna']]).item()
    return recalls


def neighbors(x, k, query=None, exclude_self=False):
    k = min(k, len(x) - int(exclude_self))
    if k < 1:
        raise ValueError('Too few cells for nearest neighbors')
    nn = NearestNeighbors(n_neighbors=k+int(exclude_self), algorithm='brute', metric='euclidean', n_jobs=1).fit(x)
    distance, index = nn.kneighbors(x if query is None else query)
    if exclude_self:
        # Remove self by identity; duplicate vectors need not put self first.
        keep = index != np.arange(len(x))[:, None]
        rows = [np.flatnonzero(row)[:k] for row in keep]
        index = np.stack([index[i, rows[i]] for i in range(len(x))])
        distance = np.stack([distance[i, rows[i]] for i in range(len(x))])
    return distance, index


def lisi(distance, index, labels, perplexity):
    """Distance-weighted LISI, matching the original LISI Hbeta definition."""
    distance = distance - distance.min(axis=1, keepdims=True)  # Stable, probability-invariant shift.
    beta = np.ones(len(index))
    low, high = np.zeros(len(index)), np.full(len(index), np.inf)
    target = np.log(min(perplexity, index.shape[1]))
    for _ in range(50):
        weights = np.exp(-distance * beta[:, None])
        sums = weights.sum(axis=1)
        probability = weights / sums[:, None]
        entropy = np.log(sums) + beta * (distance * probability).sum(axis=1)
        diff = entropy - target
        active = np.abs(diff) > 1e-5
        above, below = active & (diff > 0), active & (diff < 0)
        low[above], high[below] = beta[above], beta[below]
        beta[above] = np.where(np.isfinite(high[above]), (beta[above]+high[above])/2, beta[above]*2)
        beta[below] = (beta[below]+low[below])/2
        if not active.any():
            break
    weights = np.exp(-distance * beta[:, None])
    probability = weights / weights.sum(axis=1, keepdims=True)
    simpson = np.zeros(len(index))
    for label in np.unique(labels):
        mass = (probability * (labels[index] == label)).sum(axis=1)
        simpson += mass**2
    return 1/simpson


def cross_scores(x, y, lx, ly, k):
    _, xy = neighbors(y, max(k, 10), query=x)
    _, yx = neighbors(x, max(k, 10), query=y)
    result = {}
    pairs = {(i, int(j)) for i, row in enumerate(xy[:, :k]) for j in row}
    reverse = {(int(i), j) for j, row in enumerate(yx[:, :k]) for i in row}
    mutual = pairs & reverse
    result['mnn_pair_count'] = len(mutual)
    result['mnn_rna_coverage'] = len({i for i, _ in mutual}) / len(x)
    result['mnn_atac_coverage'] = len({j for _, j in mutual}) / len(y)
    result['mnn_directed_edge_fraction'] = 2*len(mutual)/(len(pairs)+len(reverse))
    if lx is not None and ly is not None:
        result['cross_nn_cell_type_agreement'] = np.mean([
            np.mean(lx == ly[xy[:, 0]]), np.mean(ly == lx[yx[:, 0]])]).item()
        for name, training, truth, indices in [('rna_to_atac', lx, ly, yx), ('atac_to_rna', ly, lx, xy)]:
            # Uniform kNN vote; alphabetically first label breaks ties.
            classes = np.unique(training)
            votes = np.stack([(training[indices[:, :k]] == c).sum(axis=1) for c in classes], axis=1)
            prediction = classes[votes.argmax(axis=1)]
            result['label_transfer_{}_accuracy'.format(name)] = skm.accuracy_score(truth, prediction)
            result['label_transfer_{}_macro_f1'.format(name)] = skm.f1_score(truth, prediction, average='macro', zero_division=0)
            result['label_transfer_{}_balanced_accuracy'.format(name)] = skm.balanced_accuracy_score(truth, prediction)
        result['mnn_cell_type_agreement'] = np.mean([lx[i] == ly[j] for i, j in mutual]).item() if mutual else None
    return result


class Scores:
    def __init__(self):
        self.values, self.availability = {}, []

    def add(self, name, value, reason='Computed', detail=''):
        if value is not None:
            value = float(value)
            if not np.isfinite(value):
                raise ValueError('Nonfinite metric {}'.format(name))
        self.values[name] = value
        self.availability.append(dict(metric=name, status='available' if value is not None else 'N/A', reason=reason, parameters=detail))

    def update(self, scores, detail=''):
        for name, value in scores.items():
            self.add(name, value, detail=detail)


def biological_scores(x, labels, modality, args, scores):
    import anndata as ad
    import scanpy as sc
    import scglue.metrics as legacy
    from scipy.sparse.csgraph import connected_components
    scores.add('mean_average_precision', legacy.mean_average_precision(x, labels), detail='GLUE neighbor_frac=0.01; Euclidean')
    raw = skm.silhouette_score(x, labels, metric='euclidean')
    scores.add('cell_type_asw_raw', raw, detail='Full dataset; [-1,1]; higher better')
    scores.add('avg_silhouette_width', (raw+1)/2, detail='GLUE (raw+1)/2; [0,1]; higher better')
    # Unlike legacy's degenerate-group fallback, invalid strata are explicitly excluded.
    mix, eligible = [], 0
    for label in np.unique(labels):
        mask = labels == label
        if 1 < len(np.unique(modality[mask])) < mask.sum():
            s = skm.silhouette_samples(x[mask], modality[mask])
            mix.append(np.mean(1-np.abs(s)))
            eligible += mask.sum()
    scores.add('avg_silhouette_width_batch', np.mean(mix) if mix else None,
               reason='Cell-type macro mean over eligible strata' if mix else 'No valid strata',
               detail='Modality ASW: mean_ct mean_cells(1-|s|); higher better; no donor/batch inference')
    scores.add('modality_asw_eligible_cell_fraction', eligible/len(x))
    data = ad.AnnData(X=x)
    sc.pp.neighbors(data, n_neighbors=15, n_pcs=0, use_rep='X', random_state=args.evaluation_seed, metric='euclidean')
    connection = data.obsp['connectivities']
    values = []
    for label in np.unique(labels):
        mask = labels == label
        _, components = connected_components(connection[mask][:, mask], connection='strong')
        values.append(np.bincount(components).max()/mask.sum())
    scores.add('graph_connectivity', np.mean(values), detail='GLUE Scanpy neighbors k=15; mean cell-type largest component fraction')
    try:
        import leidenalg  # noqa: F401
    except ImportError:
        for name in ['nmi_leiden_fixed', 'ari_leiden_fixed', 'normalized_mutual_info', 'ari_at_nmi_optimal_resolution', 'nmi_optimal_resolution']:
            scores.add(name, None, reason='leidenalg unavailable')
    else:
        nmis, aris, resolutions, fixed_clusters = [], [], [], None
        for resolution in np.arange(1, 21)/10:
            sc.tl.leiden(data, resolution=float(resolution), random_state=args.evaluation_seed)
            cluster = data.obs['leiden'].to_numpy()
            nmis.append(skm.normalized_mutual_info_score(labels, cluster, average_method='arithmetic'))
            aris.append(skm.adjusted_rand_score(labels, cluster))
            resolutions.append(resolution)
            if np.isclose(resolution, args.leiden_resolution):
                fixed_clusters = cluster.copy()
        if fixed_clusters is None:
            sc.tl.leiden(data, resolution=args.leiden_resolution, random_state=args.evaluation_seed)
            fixed_clusters = data.obs['leiden'].to_numpy()
        scores.add('nmi_leiden_fixed', skm.normalized_mutual_info_score(labels, fixed_clusters, average_method='arithmetic'))
        scores.add('ari_leiden_fixed', skm.adjusted_rand_score(labels, fixed_clusters))
        best = int(np.argmax(nmis))
        scores.add('normalized_mutual_info', nmis[best], detail='Legacy GLUE maximum NMI over Leiden resolutions 0.1..2.0; label-selected optimistic estimate')
        scores.add('ari_at_nmi_optimal_resolution', aris[best], detail='ARI at same label-selected resolution; exploratory')
        scores.add('nmi_optimal_resolution', resolutions[best])
    return data


def fixed_k_kbet(x, labels, modality, k):
    """Explicit fixed-k Pearson variant: all anchors, within each cell type."""
    rates, valid = [], 0
    for label in np.unique(labels):
        mask = labels == label
        batch = modality[mask]
        categories, counts = np.unique(batch, return_counts=True)
        actual_k = min(k, mask.sum()-1)
        expected = counts / mask.sum() * actual_k
        if len(categories) < 2 or actual_k < 10 or (expected < 5).any():
            continue
        _, index = neighbors(x[mask], actual_k, exclude_self=True)
        observed = np.stack([(batch[index] == c).sum(axis=1) for c in categories], axis=1)
        statistic = ((observed-expected)**2/expected).sum(axis=1)
        rates.append(np.mean(chi2.sf(statistic, len(categories)-1) < 0.05))
        valid += mask.sum()
    return (float(np.mean(rates)) if rates else None), valid/len(x)


def reconstruct_graph(info):
    import networkx as nx
    from graph_perturbation import subsample_reciprocal_pairs, randomize_topology
    original = nx.read_graphml(info['args']['prior'])
    mode, seed = info['graph_perturbation'], info['graph_seed']
    if mode == 'subsample':
        graph, metadata = subsample_reciprocal_pairs(original, info['graph_retain_fraction'], seed)
    elif mode == 'randomize':
        graph, metadata = randomize_topology(original, seed, swap_multiplier=info['graph_swap_multiplier'])
        if not metadata['completed']:
            raise ValueError('Incomplete reconstructed randomized graph')
    elif mode == 'none':
        graph, metadata = original.copy(), {'graph_seed': seed}
    else:
        raise ValueError('Unknown perturbation {}'.format(mode))
    relations = lambda g: {(u,v) for u,v,d in g.edges(data=True) if u != v and d.get('type') == 'fwd'}
    old, new = relations(original), relations(graph)
    metadata.update(original_node_count=len(original), original_relation_count=len(old), resulting_relation_count=len(new))
    for key, value in info['graph_perturbation_metadata'].items():
        if key not in metadata or metadata[key] != value:
            raise ValueError('Reconstructed graph metadata mismatch: {}'.format(key))
    nodes = sorted(original)
    old_degree = np.array([sum(v != u for v in original.successors(u)) for u in nodes])
    new_degree = np.array([sum(v != u for v in graph.successors(u)) for u in nodes])
    overlap = len(old & new)
    graph_stats = dict(
        node_count=len(graph), directed_edge_count=graph.number_of_edges(), self_loop_count=len(list(nx.selfloop_edges(graph))),
        biological_relation_count=len(new), original_relation_count=len(old),
        edge_count_fraction=len(new)/len(old), original_edge_retained_fraction=overlap/len(old),
        original_edges_retained_percent=100*overlap/len(old), edge_jaccard=overlap/len(old | new),
        perturbation_strength=1-overlap/len(old),
        degree_exact_preservation_fraction=np.mean(old_degree == new_degree),
        degree_mean_absolute_change=np.mean(abs(new_degree-old_degree)),
        degree_distribution_ks=ks_2samp(old_degree, new_degree).statistic,
        degree_mean=new_degree.mean(), degree_sd=new_degree.std(ddof=1),
        degree_q50=np.quantile(new_degree, 0.5), degree_q95=np.quantile(new_degree, 0.95),
        degree_max=new_degree.max(), degree_zero_fraction=np.mean(new_degree == 0),
        accepted_swaps=metadata.get('accepted_swaps', 0)
    )
    return graph, graph_stats


def gate_scores(run_dir, graph, diagnostics, scores):
    import scglue.models
    model_path = run_dir/'final.dill'
    # Reading a trusted project model restores weights only; never compiles/trains.
    if not model_path.is_file():
        for name in ['gate_median','gate_sd','gate_q01','gate_q05','gate_q25','gate_q75','gate_q95','gate_q99',
                     'gate_fraction_lt_0_1','gate_fraction_lt_0_5','gate_fraction_ge_0_9','gate_fraction_ge_0_95',
                     'gate_effective_edge_mass','gate_reciprocal_mean_abs_difference']:
            scores.add(name, None, reason='Individual gates absent from YAML and final.dill is unavailable')
        return
    model = scglue.models.load_model(model_path)
    if model.graph_encoder != 'gated':
        raise ValueError('Saved model is not gated')
    raw = {k:v.detach().cpu().numpy() for k,v in model.get_graph_gates().items()}
    vertices = np.asarray(model.vertices, dtype=str)
    source, target = vertices[raw['source']], vertices[raw['target']]
    if set(zip(source, target)) != set(graph.edges()) or not np.array_equal(raw['is_self_loop'], source == target):
        raise ValueError('Saved gate topology does not match reconstructed training graph')
    mask = ~raw['is_self_loop']
    gates = raw['gate'][mask].astype(float)
    if not np.isfinite(gates).all() or (gates < 0).any() or (gates > 1).any():
        raise ValueError('Invalid individual gate values')
    if not np.allclose(raw['gate'][~mask], 1):
        raise ValueError('Self-loop gates are not fixed at 1')
    if len(gates) != diagnostics['number_of_trainable_gates'] or not np.isclose(gates.mean(), diagnostics['final_gate_mean'], atol=1e-6):
        raise ValueError('Individual gates disagree with diagnostics')
    scores.add('gate_median', np.median(gates))
    scores.add('gate_sd', np.std(gates, ddof=1), detail='Sample SD across directed non-loop gates; reciprocal edges are dependent')
    for q in [0.01,0.05,0.25,0.75,0.95,0.99]:
        scores.add('gate_q{:02d}'.format(round(q*100)), np.quantile(gates, q))
    for threshold in [0.1,0.5]:
        scores.add('gate_fraction_lt_'+str(threshold).replace('.','_'), np.mean(gates < threshold))
    for threshold in [0.9,0.95]:
        scores.add('gate_fraction_ge_'+str(threshold).replace('.','_'), np.mean(gates >= threshold))
    scores.add('gate_effective_edge_mass', gates.sum(), detail='Sum of directed non-loop gates; soft mass, not hard retained edge count')
    by_edge = {(u,v):float(g) for u,v,g in zip(source[mask], target[mask], gates)}
    differences = [abs(g-by_edge[(v,u)]) for (u,v),g in by_edge.items() if u < v]
    scores.add('gate_reciprocal_mean_abs_difference', np.mean(differences))
    del model
    gc.collect()


def labels_from_obs(obs, column):
    if column not in obs or obs[column].isna().any() or obs[column].nunique() < 2:
        return None
    values = obs[column].astype(str).to_numpy()
    if set(values) <= {'scRNA-seq','scATAC-seq','RNA','ATAC','rna','atac'}:
        raise ValueError('Cell type annotation is a modality label')
    return values


def make_references(input_dir, output, args, obs):
    """Generate once from raw counts, using the existing GLUE unimodal workflow."""
    import anndata as ad
    import scanpy as sc
    import scglue.data
    references = []
    for modality in ['rna', 'atac']:
        dest = output/'references'/('{}_unirep.h5ad'.format(modality))
        supplied = input_dir/('{}_unirep.h5ad'.format(modality))
        source = supplied if supplied.is_file() else dest
        if not source.is_file() and args.references == 'derive':
            print('Deriving {} unimodal reference (GLUE workflow, dim=50)'.format(modality), flush=True)
            data = ad.read_h5ad(input_dir/(modality+'.h5ad'))
            if modality == 'rna':
                sc.pp.normalize_total(data)
                data = data[:, data.var['highly_variable']].copy()
                sc.pp.log1p(data)
                sc.pp.scale(data, max_value=10)
                sc.tl.pca(data, n_comps=50, svd_solver='auto', random_state=args.evaluation_seed)
                x = data.obsm['X_pca']
            else:
                scglue.data.lsi(data, n_components=50, use_highly_variable=False, n_iter=15, random_state=args.evaluation_seed)
                x = data.obsm['X_lsi']
            dest.parent.mkdir(parents=True, exist_ok=True)
            ad.AnnData(X=x, obs=data.obs.copy()).write_h5ad(dest, compression='gzip')
            del data
            gc.collect()
        if source.is_file():
            data = ad.read_h5ad(source)
            frame = pd.DataFrame(np.asarray(data.X), index=data.obs_names.astype(str))
            if not frame.index.is_unique or set(frame.index) != set(obs[modality].index) or not np.isfinite(frame.to_numpy()).all():
                raise ValueError('Invalid unimodal reference: {}'.format(source))
            references.append(frame.loc[obs[modality].index].to_numpy())
        else:
            references.append(None)
    return references


def evaluate_run(row, info, obs, paired, graph, graph_stats, references, args):
    import scglue.metrics as legacy
    run_dir = Path(row.run_dir)
    x = read_embedding(run_dir/'rna_latent.csv', obs['rna'].index, info['args']['dim']).to_numpy()
    y = read_embedding(run_dir/'atac_latent.csv', obs['atac'].index, info['args']['dim']).to_numpy()
    feature = read_embedding(run_dir/'feature_latent.csv', list(graph.nodes()), info['args']['dim'])
    del feature
    lr, la = [labels_from_obs(obs[m], args.cell_type) for m in ['rna','atac']]
    if args.mode == 'smoke':
        n = min(args.smoke_cells, len(x), len(y))
        rng = np.random.RandomState(args.evaluation_seed)
        chosen = np.sort(rng.choice(len(x), n, replace=False))
        x = x[chosen]
        if paired['verified']:
            positions = obs['atac'].index.get_indexer(obs['rna'].index[chosen])
        else:
            positions = np.sort(rng.choice(len(y), n, replace=False))
        y = y[positions]
        lr = lr[chosen] if lr is not None else None
        la = la[positions] if la is not None else None
        references = [references[0][chosen] if references[0] is not None else None,
                      references[1][positions] if references[1] is not None else None]
    elif paired['verified']:
        positions = obs['atac'].index.get_indexer(obs['rna'].index)
        y = y[positions]
        la = la[positions] if la is not None else None
        references = [references[0], references[1][positions] if references[1] is not None else None]
    z = np.concatenate([x,y])
    modality = np.repeat([0,1], [len(x),len(y)])
    labels = np.concatenate([lr,la]) if lr is not None and la is not None else None
    scores = Scores()
    scores.add('n_rna_evaluated', len(x))
    scores.add('n_atac_evaluated', len(y))
    if paired['verified']:
        scores.update(paired_scores(x,y,args.chunk_size), detail='Verified source correspondence; exact chunked Euclidean; ties by target index')
    else:
        for name in ['foscttm','foscttm_rna_to_atac','foscttm_atac_to_rna'] + [
                'matching_recall{}_at_{}'.format(d,k) for d in ['', '_rna_to_atac','_atac_to_rna'] for k in [1,5,10]]:
            scores.add(name, None, reason=paired['reason'])
    scores.update(cross_scores(x,y,lr,la,args.cross_k), detail='Bidirectional Euclidean cross-kNN; k={}'.format(args.cross_k))
    raw = skm.silhouette_score(z, modality)
    scores.add('modality_asw_raw', raw, detail='Raw modality silhouette [-1,1], descriptive separation, lower |s| preferred')
    scores.add('seurat_alignment_score', legacy.seurat_alignment_score(z,modality,random_state=args.evaluation_seed),
               detail='Original GLUE; neighbor_frac=.01, 4 balanced subsampling repeats; modality labels')
    distance, index = neighbors(z, int(3*args.lisi_perplexity), exclude_self=True)
    ilisi = lisi(distance,index,modality,args.lisi_perplexity)
    scores.add('ilisi', ilisi.mean(), detail='Gaussian distance-weighted Euclidean LISI; modality; mean; range 1..2')
    scores.add('ilisi_median', np.median(ilisi))
    if labels is not None:
        biological_scores(z,labels,modality,args,scores)
        clisi = lisi(distance,index,labels,args.lisi_perplexity)
        scores.add('clisi', clisi.mean(), detail='Weighted LISI; biological reference labels; smaller/closer to 1 better')
        scores.add('clisi_median', np.median(clisi))
        rate, coverage = fixed_k_kbet(z,labels,modality,args.kbet_k)
        scores.add('kbet_modality_fixed_k_rejection', rate,
                   reason='Fixed-k Pearson variant; not canonical R kBET/scIB output' if rate is not None else 'No eligible strata with expected counts >=5',
                   detail='Macro cell-type mean; alpha=.05, all anchors, no outsider adaptation, k={}'.format(args.kbet_k))
        scores.add('kbet_eligible_cell_fraction', coverage)
    else:
        for name in ['mean_average_precision','cell_type_asw_raw','avg_silhouette_width','avg_silhouette_width_batch',
                     'modality_asw_eligible_cell_fraction','graph_connectivity','nmi_leiden_fixed','ari_leiden_fixed',
                     'normalized_mutual_info','ari_at_nmi_optimal_resolution','nmi_optimal_resolution','clisi','clisi_median',
                     'cross_nn_cell_type_agreement','mnn_cell_type_agreement','kbet_modality_fixed_k_rejection','kbet_eligible_cell_fraction'] + [
                         'label_transfer_{}_{}'.format(d,m) for d in ['rna_to_atac','atac_to_rna'] for m in ['accuracy','macro_f1','balanced_accuracy']]:
            scores.add(name,None,reason='Missing/noncomplete/multiclass cell-type reference annotation')
    scores.add('kbet_canonical', None, reason='Canonical R kBET/scIB dependency unavailable; separately named fixed-k modality variant is reported')
    scores.add('batch_asw_independent', None, reason='Only modality labels and constant SeuratProject sample identifier; no independent batch/donor annotation')
    scores.add('ilisi_independent_batch', None, reason='No independent batch/donor annotation; ilisi uses modality')
    if all(r is not None for r in references):
        scores.add('neighbor_conservation', legacy.neighbor_conservation(z,np.concatenate(references),modality),
                   detail='Original GLUE Jaccard; k=round(.01*n_combined); 50D PCA/LSI from raw counts; derived evaluation references, not saved training representations')
    else:
        scores.add('neighbor_conservation',None,reason='No unimodal references; use --references derive in full CPU batch evaluation')
    scores.update(graph_stats, detail='Biological reciprocal pairs exclude self-loops; graph rebuilt and saved metadata verified')
    diagnostics = read_info(run_dir/'gate_diagnostics.yaml')
    mapping = {'final_gate_mean':'gate_mean','final_gate_min':'gate_min','final_gate_max':'gate_max',
               'initial_gate_mean':'gate_initial_mean','number_of_trainable_gates':'gate_count',
               'maximum_absolute_gate_logit_change':'gate_max_absolute_logit_change'}
    for key,name in mapping.items():
        scores.add(name,diagnostics.get(key),detail='Saved gate diagnostics; directed non-loop edges only')
    scores.add('gate_mean_change_from_initial', diagnostics['final_gate_mean']-diagnostics['initial_gate_mean'])
    gate_scores(run_dir,graph,diagnostics,scores)
    meta = dict(condition=row.condition, model_seed=int(row.model_seed), graph_seed=int(row.graph_seed),
                task_id=int(row.task_id), evaluation_mode=args.mode, run_dir=str(run_dir))
    return dict(metadata=meta, metrics=scores.values,
                availability=[dict(**meta, **entry) for entry in scores.availability])


def aggregate(frame, metric_names):
    summaries, differences = [], []
    baseline = frame[frame.condition == 'original'].set_index('model_seed')
    for name in metric_names:
        for condition, group in frame.groupby('condition', sort=False):
            values = pd.to_numeric(group[name], errors='coerce')
            summaries.append(dict(condition=condition, metric=name, n=int(values.count()), mean=values.mean(), sd=values.std(ddof=1)))
            aligned = pd.to_numeric(group.set_index('model_seed')[name],errors='coerce').subtract(
                pd.to_numeric(baseline[name],errors='coerce'))
            valid = values.dropna()
            base = pd.to_numeric(baseline[name], errors='coerce')
            base_mean = base.mean()
            mean = valid.mean()
            # Percent change is not interpretable for signed/centred silhouette or ARI.
            percent_valid = not ('asw_raw' in name or 'ari' in name or 'change' in name) and pd.notna(base_mean) and base_mean > 0
            differences.append(dict(condition=condition,metric=name,n=int(aligned.count()),
                baseline_mean=base_mean,mean=mean,difference_from_baseline_mean=mean-base_mean,
                seed_matched_difference_mean=aligned.mean(),seed_matched_difference_sd=aligned.std(ddof=1),
                relative_percent_change=100*(mean-base_mean)/base_mean if percent_valid else np.nan,
                relative_change_reason='100*(condition mean-baseline mean)/baseline mean' if percent_valid else 'N/A: missing/zero baseline or signed/centred metric'))
    return pd.DataFrame(summaries), pd.DataFrame(differences)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['preflight','smoke','full','report'],default='preflight')
    p.add_argument('--manifest',type=Path,default=EXPERIMENT/'manifest.csv')
    p.add_argument('--output',type=Path,default=EXPERIMENT/'reports/full')
    p.add_argument('--input-dir',type=Path,default=INPUT)
    p.add_argument('--pairing-provenance',type=Path,default=ROOT/'data/collect/10x-Multiome-Pbmc10k.ipynb')
    p.add_argument('--cell-type',default='cell_type')
    p.add_argument('--evaluation-seed',type=int,default=0)
    p.add_argument('--chunk-size',type=int,default=256)
    p.add_argument('--working-memory-mb',type=int,default=64)
    p.add_argument('--cross-k',type=int,default=15)
    p.add_argument('--lisi-perplexity',type=float,default=30)
    p.add_argument('--kbet-k',type=int,default=50)
    p.add_argument('--leiden-resolution',type=float,default=1.0)
    p.add_argument('--references',choices=['existing','derive'],default='derive')
    p.add_argument('--smoke-cells',type=int,default=100)
    p.add_argument('--allow-login',action='store_true',help='Explicit override for full evaluation outside a scheduler')
    args = p.parse_args(argv)
    if min(args.chunk_size,args.working_memory_mb,args.cross_k,args.kbet_k,args.smoke_cells,args.lisi_perplexity,args.leiden_resolution) <= 0:
        p.error('Evaluation sizes/resolution must be positive')
    if args.mode == 'full' and not os.environ.get('SLURM_JOB_ID') and not args.allow_login:
        p.error('Full evaluation requires a Slurm allocation; submit evaluate.sbatch')
    if args.mode == 'smoke' and args.output.resolve() == (EXPERIMENT/'reports/full').resolve():
        p.error('Smoke output must be distinct from reports/full')
    return args


def main(argv=None):
    args = parse_args(argv)
    output = args.output.resolve()
    results = EXPERIMENT/'results'
    if output == results or results in output.parents or output in results.parents:
        raise ValueError('Output must not overlap training results')
    if output == args.input_dir.resolve() or args.input_dir.resolve() in output.parents:
        raise ValueError('Output must not overlap source inputs')
    output.mkdir(parents=True,exist_ok=True)
    if args.mode == 'report':
        from reporting import generate_report
        generate_report(output)
        return
    np.random.seed(args.evaluation_seed)
    rows = pd.read_csv(args.manifest)
    if len(rows) != 18 or set(rows.condition) != set(CONDITIONS) or rows[['condition','model_seed']].duplicated().any():
        raise ValueError('Expected the six-condition, three-seed manifest')
    if any(set(g.model_seed) != {0,1,2} for _,g in rows.groupby('condition')) or not (rows.graph_seed == 0).all():
        raise ValueError('Unexpected model or graph seeds')
    obs = {m:read_obs(args.input_dir/(m+'.h5ad')) for m in ['rna','atac']}
    paired = verify_pairs(obs['rna'],obs['atac'],args.pairing_provenance)
    write_json(output/'pairing_verification.json',paired)
    infos, fingerprints = {}, []
    for row in rows.itertuples(index=False):
        run = Path(row.run_dir)
        info = read_info(run/'run_info.yaml')
        if info['args']['random_seed'] != row.model_seed or info['graph_seed'] != row.graph_seed or info['graph_perturbation'] != row.graph_perturbation:
            raise ValueError('Manifest/run metadata disagreement: {}'.format(run))
        if row.graph_perturbation == 'subsample' and info['graph_retain_fraction'] != row.retain_fraction:
            raise ValueError('Retention fraction disagreement')
        if row.graph_perturbation == 'randomize' and info['graph_swap_multiplier'] != row.swap_multiplier:
            raise ValueError('Swap multiplier disagreement')
        for m in ['rna','atac']:
            if Path(info['args']['input_'+m]).resolve() != (args.input_dir/(m+'.h5ad')).resolve():
                raise ValueError('Source path disagrees with saved training metadata')
        manifest_copy = pd.read_csv(run/'manifest.csv')
        if not manifest_copy.equals(rows):
            raise ValueError('Saved manifest differs from selected experiment manifest')
        infos[int(row.task_id)] = info
        files = ['rna_latent.csv','atac_latent.csv','feature_latent.csv','gate_diagnostics.yaml','run_info.yaml','manifest.csv']
        if (run/'final.dill').is_file(): files.append('final.dill')
        fingerprints.append({str(run/f):sha256(run/f) for f in files})
    versions = {}
    for package in ['numpy','pandas','scipy','scikit-learn','scanpy','anndata','torch','dill','leidenalg','igraph','matplotlib']:
        try: versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: versions[package] = 'not installed'
    config = {k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items() if k not in ['mode','allow_login']}
    config.update(evaluation_mode=args.mode, python=sys.version, versions=versions,
                  numeric_threads={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMBA_NUM_THREADS']},
                  source_hashes={str(p.relative_to(ROOT)):sha256(p) for p in [Path(__file__).resolve(),Path(__file__).resolve().with_name('reporting.py'),Path(__file__).resolve().with_name('methodology.md'),Path(__file__).resolve().with_name('REPRODUCE.md'),ROOT/'scglue/metrics.py',ROOT/'scglue/data.py',ROOT/'evaluation/workflow/scripts/graph_perturbation.py']},
                  original_graph_sha256={str(p):sha256(p) for p in {Path(i['args']['prior']) for i in infos.values()}},
                  supplied_references_sha256={str(p):sha256(p) for p in args.input_dir.glob('*_unirep.h5ad')},
                  source_inputs={str(args.input_dir/(m+'.h5ad')):dict(size=(args.input_dir/(m+'.h5ad')).stat().st_size,mtime_ns=(args.input_dir/(m+'.h5ad')).stat().st_mtime_ns) for m in ['rna','atac']},
                  run_input_sha256=fingerprints, manifest_sha256=sha256(args.manifest), pairing=paired)
    digest = hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    config['fingerprint'] = digest
    config_path = output/'evaluation_config.json'
    if config_path.exists() and json.loads(config_path.read_text()).get('fingerprint') != digest:
        raise ValueError('Output configuration/input changed; choose a new --output directory')
    write_json(config_path,config)
    import networkx as nx
    prior_nodes = {path:list(nx.read_graphml(path).nodes()) for path in {i['args']['prior'] for i in infos.values()}}
    audit = []
    for row in rows.itertuples(index=False):
        info = infos[int(row.task_id)]
        for m in ['rna','atac']:
            emb = read_embedding(Path(row.run_dir)/(m+'_latent.csv'),obs[m].index,info['args']['dim'])
            audit.append(dict(condition=row.condition,model_seed=int(row.model_seed),modality=m,n_cells=len(emb),dimensions=emb.shape[1],identifier_set_verified=True,finite=True))
        feature=read_embedding(Path(row.run_dir)/'feature_latent.csv',prior_nodes[info['args']['prior']],info['args']['dim'])
        audit.append(dict(condition=row.condition,model_seed=int(row.model_seed),modality='feature',n_cells=len(feature),dimensions=feature.shape[1],identifier_set_verified=True,finite=True))
    pd.DataFrame(audit).to_csv(output/'validation_audit.csv',index=False)
    write_json(output/'dataset_metadata.json', {m:dict(n_cells=len(o),columns=list(o.columns),
               cell_type_counts=o[args.cell_type].astype(str).value_counts().to_dict() if args.cell_type in o else {},
               sample_values=o['orig.ident'].astype(str).unique().tolist() if 'orig.ident' in o else []) for m,o in obs.items()})
    print('Validated all 18 runs. Pairing: {}'.format(paired),flush=True)
    if args.mode == 'preflight':
        write_json(output/'status.json',dict(status='preflight_complete',n_validated_runs=18,metrics_computed=False))
        return
    write_json(output/'status.json',dict(status='running',slurm_job_id=os.environ.get('SLURM_JOB_ID'),started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
    references = make_references(args.input_dir,output,args,obs) if args.mode == 'full' else [None,None]
    if args.mode == 'full':
        reference_provenance={'evaluation_seed':args.evaluation_seed,'dimension':50,
            'files':{str(p):sha256(p) for p in list((output/'references').glob('*.h5ad'))+list(args.input_dir.glob('*_unirep.h5ad'))}}
        previous=output/'reference_provenance.json'
        if previous.exists() and json.loads(previous.read_text()) != reference_provenance:
            raise ValueError('Unimodal reference files changed; refusing reuse of checkpoints')
        write_json(previous,reference_provenance)
    records, graph_cache = [], {}
    selected = rows.iloc[:1] if args.mode == 'smoke' else rows
    with config_context(working_memory=args.working_memory_mb):
        for row in selected.itertuples(index=False):
            checkpoint = output/'checkpoints'/('task_{}.json'.format(row.task_id))
            if checkpoint.exists():
                record = json.loads(checkpoint.read_text())
                if record['fingerprint'] != digest: raise ValueError('Stale checkpoint')
                print('Reusing validated checkpoint task {}'.format(row.task_id),flush=True)
            else:
                print('Evaluating task {}: {} seed {}'.format(row.task_id,row.condition,row.model_seed),flush=True)
                start = time.monotonic()
                info = infos[int(row.task_id)]
                key = row.condition
                if key not in graph_cache:
                    graph_cache[key] = reconstruct_graph(info)
                else:
                    # Every seed must document the same graph realization.
                    first = infos[int(rows[rows.condition == key].iloc[0].task_id)]
                    if first['graph_perturbation_metadata'] != info['graph_perturbation_metadata'] or first['args']['prior'] != info['args']['prior']:
                        raise ValueError('Within-condition graph metadata differs')
                record = evaluate_run(row,info,obs,paired,*graph_cache[key],references,args)
                record.update(fingerprint=digest,elapsed_seconds=time.monotonic()-start)
                write_json(checkpoint,record)
                print('Finished task {} in {:.1f}s'.format(row.task_id,record['elapsed_seconds']),flush=True)
            records.append(record)
    frame = pd.DataFrame([dict(**r['metadata'],**r['metrics']) for r in records])
    names = sorted(set(name for r in records for name in r['metrics']))
    frame.to_csv(output/'per_run_metrics.csv',index=False,na_rep='N/A')
    summary, comparison = aggregate(frame,names)
    summary.to_csv(output/'summary_metrics.csv',index=False,na_rep='N/A')
    comparison.to_csv(output/'baseline_comparison.csv',index=False,na_rep='N/A')
    graph_names = list(next(iter(graph_cache.values()))[1]) if graph_cache else list(records[0]['metrics'].keys())
    # Resume can leave graph_cache empty; explicit names keep graph table distinct.
    if not graph_cache:
        graph_names = ['node_count','directed_edge_count','self_loop_count','biological_relation_count','original_relation_count','edge_count_fraction','original_edge_retained_fraction','original_edges_retained_percent','edge_jaccard','perturbation_strength','degree_exact_preservation_fraction','degree_mean_absolute_change','degree_distribution_ks','degree_mean','degree_sd','degree_q50','degree_q95','degree_max','degree_zero_fraction','accepted_swaps']
    frame[['condition','model_seed','graph_seed']+graph_names].to_csv(output/'graph_statistics.csv',index=False,na_rep='N/A')
    frame[['condition','model_seed','graph_seed']+[n for n in names if n.startswith('gate_')]].to_csv(output/'gate_statistics.csv',index=False,na_rep='N/A')
    pd.DataFrame([a for r in records for a in r['availability']]).to_csv(output/'metric_availability.csv',index=False)
    from reporting import generate_report
    generate_report(output)
    write_json(output/'status.json',dict(status='complete' if args.mode == 'full' else 'smoke_complete',
               n_evaluated_runs=len(records),slurm_job_id=os.environ.get('SLURM_JOB_ID'),completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
    print('Outputs generated at {}'.format(output),flush=True)


if __name__ == '__main__':
    main()
