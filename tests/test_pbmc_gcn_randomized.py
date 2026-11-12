"""Regression checks for isolation, exact graph attributes and matched comparisons."""
import importlib.util
import json
from pathlib import Path
import sys
import networkx as nx
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts'
sys.path.insert(0,str(SCRIPTS))
# The extension's common module is needed even when the original tests ran first.
spec=importlib.util.spec_from_file_location('randomized_common',SCRIPTS/'common.py')
common=importlib.util.module_from_spec(spec);spec.loader.exec_module(common)


def load(name):
    previous=sys.modules.get('common');sys.modules['common']=common
    try:
        spec=importlib.util.spec_from_file_location('randomized_'+name,SCRIPTS/(name+'.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    finally:
        if previous is None: sys.modules.pop('common',None)
        else: sys.modules['common']=previous


def test_manifest_keeps_original_task_identity_and_adds_only_three_seeds():
    original=common.base.validate_manifest()
    random=common.validate_manifest()
    combined=common.validate_manifest(common.EXPERIMENT/'combined_manifest.csv')
    pd.testing.assert_frame_equal(combined.iloc[:15].reset_index(drop=True),original)
    assert random.model_seed.tolist()==[0,1,2]
    assert len(combined)==18 and combined.condition.nunique()==6
    assert combined.groupby('condition').model_seed.apply(list).to_dict()=={c:[0,1,2] for c in common.CONDITIONS}
    assert set(original.run_dir).isdisjoint(set(random.run_dir))


def test_exact_comparator_rejects_attribute_change_even_with_same_statistics():
    prepare=load('prepare')
    graph=nx.DiGraph();graph.add_edge('g','p',weight=1.,sign=1,type='fwd',dist=42)
    altered=graph.copy();altered['g']['p']['dist']=43
    assert graph.number_of_edges()==altered.number_of_edges()
    with pytest.raises(ValueError,match='attributes'):prepare.exact_equal(graph,altered)


def test_real_randomized_preservation_and_all_gated_proofs():
    prepare=load('prepare')
    original=nx.read_graphml(common.PRIOR)
    random=nx.read_graphml(common.EXPERIMENT/'graphs/randomized.graphml.gz')
    prepare.preservation(original,random)
    proof=json.loads((common.EXPERIMENT/'validation/graph_verification.json').read_text())['randomized']
    assert common.edge_digest(random)==proof['edge_identity_and_attributes_sha256']
    assert len(proof['gated_checkpoints'])==3
    assert all(p['exact_checkpoint_edge_identities'] and p['exact_reconstructed_edge_attributes'] for p in proof['gated_checkpoints'])
    assert proof['metadata']['accepted_swaps']==134930
    assert proof['metadata']['original_relation_overlap']==22
    for path,digest in proof['protected_files_sha256'].items():assert common.sha(path)==digest


def test_metric_source_matches_completed_gated_report_except_optional_gates():
    prepare=load('prepare')
    config=json.loads((common.GATED/'reports/full/evaluation_config.json').read_text())
    restored,proof=prepare.completed_evaluator_source(config)
    assert proof['exact_completed_source_restored']
    assert common.sha(common.EXPERIMENT/'validation/completed_gated_evaluate.py')==proof['completed_evaluator_sha256']
    assert 'include_gates' not in restored


def test_randomized_training_arguments_match_existing_non_graph_configuration():
    train=load('train')
    spec=importlib.util.spec_from_file_location('existing_train',common.BASE/'scripts/train.py')
    # Existing training's runner_arguments only uses shared settings and passed row.
    previous=sys.modules.get('common');sys.modules['common']=common.base
    try:
        existing=importlib.util.module_from_spec(spec);spec.loader.exec_module(existing)
    finally:
        if previous is None:sys.modules.pop('common',None)
        else:sys.modules['common']=previous
    for row in common.validate_manifest().itertuples(index=False):
        assert train.runner_arguments(row,Path('/tmp/example'),common.INPUT,False)==existing.runner_arguments(row,Path('/tmp/example'),common.INPUT,False)
        args=train.runner_arguments(row,Path('/tmp/example'),common.INPUT,False)
        assert '--require-converge' in args
        assert not any('gate' in a or 'attention' in a for a in args)


def test_comparison_seed_alignment_sd_and_gate_exclusion():
    sys.path.insert(0,str(common.GATED/'scripts'))
    report=load('gcn_report')
    frame=pd.DataFrame([dict(condition=c,model_seed=s,graph_seed=0,foscttm=float(s)) for c in common.CONDITIONS for s in range(3)])
    gated=frame.copy();gated['foscttm']+=.5;gated['gate_mean']=.95
    per_seed,summary=report.compare_models(frame,gated.sample(frac=1,random_state=7))
    assert len(per_seed)==18 and len(summary)==6
    np.testing.assert_allclose(summary.gcn_sd,1.)
    np.testing.assert_allclose(summary.seed_matched_difference_mean,-.5)
    assert not summary.metric.str.startswith('gate_').any()
    with pytest.raises(ValueError,match='exactly'):report.compare_models(frame.iloc[:-1],gated)
    with pytest.raises(ValueError,match='Gate'):report.compare_models(gated,gated)


def test_submission_requires_smoke_and_depends_on_both_arrays(tmp_path,monkeypatch):
    pipeline=load('submit_pipeline')
    experiment=tmp_path/'extension';validation=experiment/'validation';validation.mkdir(parents=True)
    original=tmp_path/'original';original.mkdir()
    (original/'submission.json').write_text(json.dumps(dict(training_array_job_id='64840335',evaluation_job_id='64840336')))
    (validation/'frozen_inputs.json').write_text('{}')
    proof=dict(status='passed',evaluation_supports_gcn_without_gates=True,
        frozen_inputs_sha256=common.sha(validation/'frozen_inputs.json'),job_id='123')
    (validation/'smoke_success.json').write_text(json.dumps(proof))
    (validation/'tests.json').write_text('{"status":"passed"}')
    monkeypatch.setattr(pipeline,'EXPERIMENT',experiment);monkeypatch.setattr(pipeline,'BASE',original)
    monkeypatch.setattr(pipeline,'verify_freeze',lambda:None)
    rows=common.validate_manifest().copy();rows.run_dir=[str(tmp_path/('seed_'+str(s))) for s in range(3)]
    monkeypatch.setattr(pipeline,'validate_manifest',lambda *args:rows)
    calls=[]
    def submit(script,extra=None):
        calls.append((script,extra));return str(1000+len(calls))
    monkeypatch.setattr(pipeline,'submit',submit)
    pipeline.main()
    assert len(calls)==2 and calls[0][0].name=='train_array.sbatch'
    assert calls[1][1]==['--dependency=afterok:64840335:1001','--kill-on-invalid-dep=yes']
    assert json.loads((experiment/'submission.json').read_text())['combined_gcn_runs']==18
    pipeline.main();assert len(calls)==2  # No duplicate array/evaluation.
    proof['status']='failed';(validation/'smoke_success.json').write_text(json.dumps(proof))
    with pytest.raises(ValueError,match='smoke'):pipeline.main()
    assert len(calls)==2
