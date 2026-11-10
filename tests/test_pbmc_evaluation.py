"""Scientific validity and failure-path tests for the read-only PBMC evaluator."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.spatial.distance import cdist

SCRIPT = Path(__file__).resolve().parents[1]/'evaluation/pbmc_graph_perturbation/scripts/evaluate.py'
spec = importlib.util.spec_from_file_location('pbmc_evaluation', SCRIPT)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_embeddings_align_by_identity_not_row_order(tmp_path):
    path = tmp_path/'embedding.csv'
    pd.DataFrame([[2.,3.],[0.,1.]], index=['b','a']).to_csv(path,header=False)
    result = evaluation.read_embedding(path,['a','b'],2)
    np.testing.assert_array_equal(result.to_numpy(),[[0,1],[2,3]])
    with pytest.raises(ValueError,match='identifier sets'):
        evaluation.read_embedding(path,['a','c'],2)


@pytest.mark.parametrize('values,ids', [([[np.nan,1],[2,3]],['a','b']), ([[1,2],[2,3]],['a','a'])])
def test_invalid_embeddings_fail(tmp_path,values,ids):
    path = tmp_path/'embedding.csv'
    pd.DataFrame(values,index=ids).to_csv(path,header=False)
    with pytest.raises(ValueError): evaluation.read_embedding(path)


def test_chunked_foscttm_matches_dense_definition():
    x = np.array([[0.,0.],[2.,0.],[5.,1.],[7.,0.]])
    y = np.array([[1.,0.],[5.,0.],[4.,2.],[8.,0.]])
    d = cdist(x,y)
    expected = np.mean([(d<np.diag(d)[:,None]).mean(),(d<np.diag(d)[None,:]).mean()])
    for chunk in [1,3,20]:
        scores=evaluation.paired_scores(x,y,chunk)
        assert scores['foscttm'] == pytest.approx(expected)
        assert scores['matching_recall_at_5'] == 1
        assert scores['matching_recall_at_10'] == 1


def test_paired_ties_are_not_closer():
    scores=evaluation.paired_scores(np.zeros((3,2)),np.zeros((3,2)),1)
    assert scores['foscttm'] == 0
    assert scores['matching_recall_at_1'] == pytest.approx(1/3)


def test_neighbor_self_exclusion_with_duplicate_vectors():
    x=np.zeros((5,2))
    _,indices=evaluation.neighbors(x,3,exclude_self=True)
    assert indices.shape == (5,3)
    assert not (indices == np.arange(5)[:,None]).any()


def test_lisi_pure_and_evenly_mixed_neighborhoods():
    distance=np.ones((2,4))
    indices=np.array([[0,1,2,3],[4,5,6,7]])
    labels=np.array([0,0,0,0,0,0,1,1])
    np.testing.assert_allclose(evaluation.lisi(distance,indices,labels,4),[1,2])


def test_label_transfer_and_mutual_coverage():
    x=np.array([[0.,0.],[10.,0.],[0.,1.],[10.,1.]])
    labels=np.array(['A','B','A','B'])
    scores=evaluation.cross_scores(x,x+.01,labels,labels,1)
    assert scores['mnn_pair_count'] == 4
    assert scores['mnn_directed_edge_fraction'] == 1
    assert scores['label_transfer_rna_to_atac_macro_f1'] == 1
    assert scores['label_transfer_atac_to_rna_balanced_accuracy'] == 1


def test_matching_ids_without_provenance_does_not_establish_pairing(tmp_path):
    obs=pd.DataFrame({'protocol':['10x Multiome']*2,'dataset':['10x-Multiome-Pbmc10k-RNA']*2,
                      'orig.ident':['SeuratProject']*2},index=['a','b'])
    evidence=evaluation.verify_pairs(obs,obs,tmp_path/'absent.ipynb')
    assert not evidence['verified']


def test_supported_pairing_provenance_and_mismatched_sample(tmp_path):
    source=SCRIPT.parents[3]/'data/collect/10x-Multiome-Pbmc10k.ipynb'
    obs=pd.DataFrame({'protocol':['10x Multiome']*2,'dataset':['10x-Multiome-Pbmc10k-RNA']*2,
                      'orig.ident':['SeuratProject']*2},index=['a','b'])
    other=obs.copy().iloc[::-1]
    other['dataset']='10x-Multiome-Pbmc10k-ATAC'
    assert evaluation.verify_pairs(obs,other,source)['verified']
    other.loc['a','orig.ident']='different_sample'
    assert not evaluation.verify_pairs(obs,other,source)['verified']


def test_modality_is_never_biological_annotation():
    with pytest.raises(ValueError,match='modality label'):
        evaluation.labels_from_obs(pd.DataFrame({'cell_type':['RNA','ATAC']}),'cell_type')
    assert evaluation.labels_from_obs(pd.DataFrame({'domain':['RNA','ATAC']}),'cell_type') is None


def test_ddof_one_baseline_differences_and_signed_percent_na():
    frame=pd.DataFrame({'condition':['original']*3+['retain_50']*3,
                        'model_seed':[0,1,2,0,1,2], 'score':[1.,2.,3.,2.,4.,6.],
                        'cell_type_asw_raw':[-.1,0,.1,.1,.2,.3]})
    summary,comparison=evaluation.aggregate(frame,['score','cell_type_asw_raw'])
    baseline=summary[(summary.condition=='original')&(summary.metric=='score')].iloc[0]
    assert baseline['sd'] == 1
    change=comparison[(comparison.condition=='retain_50')&(comparison.metric=='score')].iloc[0]
    assert change.seed_matched_difference_mean == 2
    assert change.seed_matched_difference_sd == 1
    assert change.relative_percent_change == 100
    assert comparison.loc[comparison.metric=='cell_type_asw_raw','relative_percent_change'].isna().all()


def test_unavailable_metrics_remain_na_and_singleton_sd_is_na():
    frame=pd.DataFrame({'condition':['original'],'model_seed':[0],'absent':[None],'score':[.5]})
    summary,comparison=evaluation.aggregate(frame,['absent','score'])
    assert summary.loc[summary.metric=='absent','n'].item()==0
    assert summary.loc[summary.metric=='score','sd'].isna().all()
    assert comparison.relative_percent_change.isna().iloc[0]


def test_safe_yaml_allows_pathlib_but_rejects_arbitrary_objects(tmp_path):
    path=tmp_path/'info.yaml'
    path.write_text('input: !!python/object/apply:pathlib.PosixPath [/, tmp, file]\n')
    assert evaluation.read_info(path)['input']=='/tmp/file'
    path.write_text('input: !!python/object/apply:os.system ["echo unexpected"]\n')
    with pytest.raises(Exception): evaluation.read_info(path)


def test_full_evaluation_requires_scheduler(monkeypatch):
    monkeypatch.delenv('SLURM_JOB_ID',raising=False)
    with pytest.raises(SystemExit): evaluation.parse_args(['--mode','full'])
    with pytest.raises(SystemExit): evaluation.parse_args(['--mode','smoke'])


def test_graph_reconstruction_checks_metadata_and_preserved_degree(tmp_path):
    import networkx as nx
    from graph_perturbation import randomize_topology
    graph=nx.DiGraph()
    for i in range(4):
        g,p='g'+str(i),'p'+str(i)
        graph.add_edge(g,p,type='fwd',weight=1.,sign=1)
        graph.add_edge(p,g,type='rev',weight=1.,sign=1)
    for node in list(graph): graph.add_edge(node,node,type='loop',weight=1.,sign=1)
    path=tmp_path/'original.graphml'
    nx.write_graphml(graph,path)
    _,metadata=randomize_topology(graph,0,swap_multiplier=2)
    metadata.update(original_node_count=8,original_relation_count=4,resulting_relation_count=4)
    info={'args':{'prior':str(path)},'graph_perturbation':'randomize','graph_seed':0,
          'graph_swap_multiplier':2.,'graph_perturbation_metadata':metadata}
    _,stats=evaluation.reconstruct_graph(info)
    assert stats['degree_exact_preservation_fraction']==1
    assert stats['degree_distribution_ks']==0
    assert stats['edge_count_fraction']==1
    info['graph_perturbation_metadata']['accepted_swaps']+=1
    with pytest.raises(ValueError,match='metadata mismatch'):evaluation.reconstruct_graph(info)
