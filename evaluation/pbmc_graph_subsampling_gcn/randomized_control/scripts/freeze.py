"""Freeze new extension only, leaving the existing experiment freeze intact."""
import json
from common import *


def main():
    base.verify_freeze();validate_manifest();validate_manifest(EXPERIMENT/'combined_manifest.csv')
    graph=json.loads((EXPERIMENT/'validation/graph_verification.json').read_text())['randomized']
    tests=json.loads((EXPERIMENT/'validation/tests.json').read_text())
    if graph['status']!='passed' or tests['status']!='passed': raise ValueError('Graph verification and tests required')
    files=list((EXPERIMENT/'scripts').glob('*.py'))+list(EXPERIMENT.glob('*.sbatch'))+[
        EXPERIMENT/'README.md',EXPERIMENT/'manifest.csv',EXPERIMENT/'combined_manifest.csv',
        EXPERIMENT/'graphs/randomized.graphml.gz',EXPERIMENT/'validation/graph_verification.json',
        EXPERIMENT/'validation/tests.json',EXPERIMENT/'validation/completed_gated_evaluate.py',WORKTREE/'tests/test_pbmc_gcn_randomized.py']
    files+=list((EXPERIMENT/'configurations').glob('*.json'))
    files += [Path(p) for p in graph['protected_files_sha256']]
    for proof in graph['gated_checkpoints']:
        files += [Path(proof['checkpoint']),Path(proof['checkpoint']).with_name('run_info.yaml')]
    for name in ['per_run_metrics.csv','summary_metrics.csv','evaluation_config.json','status.json','reference_provenance.json']:
        files.append(GATED/'reports/full'/name)
    files+=list((GATED/'reports/full/references').glob('*_unirep.h5ad'))
    config=json.loads((GATED/'reports/full/evaluation_config.json').read_text())
    from prepare import completed_evaluator_source
    _,source_proof=completed_evaluator_source(config)
    if source_proof!=graph['metric_source_equivalence']:raise ValueError('Metric source evidence differs')
    for relative,digest in config['source_hashes'].items():
        # Gate-free support is verified against the exact restored completed source.
        # Reporting was extended by the existing GCN experiment for five-condition
        # plotting; figures are newly generated, while numerical metrics are frozen.
        if relative not in ['evaluation/pbmc_graph_perturbation/scripts/evaluate.py',
                            'evaluation/pbmc_graph_perturbation/scripts/reporting.py'] and sha(WORKTREE/relative)!=digest:
            raise ValueError('Completed GATED source changed: '+relative)
        files.append(WORKTREE/relative)
    frozen=dict(base_frozen_inputs_sha256=sha(BASE/'validation/frozen_inputs.json'),
        extension_files_sha256={str(p):sha(p) for p in sorted(set(files))},
        graph_seed=0,model_seeds=[0,1,2],new_training_tasks=3,total_gcn_runs=18,conditions=CONDITIONS,
        architecture='original_glue_gcn',shared_training_settings=SHARED,
        metric_source_equivalence=source_proof,
        plotting_source=dict(completed_sha256=config['source_hashes']['evaluation/pbmc_graph_perturbation/scripts/reporting.py'],
            current_sha256=sha(GATED/'scripts/reporting.py'),note='Existing GCN-compatible condition ordering; current plotting source frozen for the new report'))
    path=EXPERIMENT/'validation/frozen_inputs.json'
    if path.exists() and json.loads(path.read_text())!=frozen: raise ValueError('Refuse to overwrite changed extension freeze')
    if not path.exists():save_json(path,frozen)
    verify_freeze()
    print('Extension frozen; original manifest, code and inputs unchanged.',flush=True)


if __name__=='__main__':main()
