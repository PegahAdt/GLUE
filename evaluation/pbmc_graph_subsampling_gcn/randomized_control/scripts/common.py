"""Separate extension; never change the original 15-run manifest or launchers."""
import importlib.util
import json
from pathlib import Path
import pandas as pd

BASE = Path('/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn')
spec = importlib.util.spec_from_file_location('frozen_gcn_common', BASE/'scripts/common.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
WORKTREE, ORIGINAL, INPUT, PRIOR, GATED, DATASET, SHARED = (
    base.WORKTREE, base.ORIGINAL, base.INPUT, base.PRIOR, base.GATED, base.DATASET, base.SHARED)
EXPERIMENT = BASE/'randomized_control'
CONDITIONS = base.CONDITIONS + ['randomized']
info, sha, save_json, edge_digest = base.info, base.sha, base.save_json, base.edge_digest
use_original, verify_model = base.use_original, base.verify_model


def validate_manifest(path=None):
    path = Path(path or EXPERIMENT/'manifest.csv')
    original = base.validate_manifest()
    frame = pd.read_csv(path)
    expected = []
    for seed in range(3):
        expected.append(dict(task_id=seed, condition='randomized', graph_perturbation='randomize',
            retain_fraction=1., graph_seed=0, model_seed=seed,
            graph_path=str(EXPERIMENT/'graphs/randomized.graphml.gz'),
            run_dir=str(BASE/'results'/DATASET/'randomized'/'graph_seed:0'/('model_seed:'+str(seed)))))
    random = pd.DataFrame(expected)
    if path.name == 'combined_manifest.csv':
        random.task_id += 15
        expected_frame = pd.concat([original, random], ignore_index=True)
    else:
        expected_frame = random
    if not frame.equals(expected_frame):
        raise ValueError('Extension manifest differs from exact expected configurations')
    return frame


def verify_freeze():
    original = base.verify_freeze()
    frozen = json.loads((EXPERIMENT/'validation/frozen_inputs.json').read_text())
    for filename, digest in frozen['extension_files_sha256'].items():
        if sha(filename) != digest:
            raise ValueError('Frozen extension input/code changed: '+filename)
    if frozen['base_frozen_inputs_sha256'] != sha(BASE/'validation/frozen_inputs.json'):
        raise ValueError('Original experiment freeze changed')
    validate_manifest(); validate_manifest(EXPERIMENT/'combined_manifest.csv')
    return original
