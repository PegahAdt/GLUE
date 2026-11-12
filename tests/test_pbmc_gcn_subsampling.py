"""Validate original architecture, exact graph subsets and gate-free evaluation."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'evaluation/pbmc_graph_subsampling_gcn/scripts'
sys.path.insert(0,str(SCRIPTS))
import common
common.use_original()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


train=load('gcn_train_test',SCRIPTS/'train.py')
prepare=load('gcn_prepare_test',SCRIPTS/'prepare.py')
core=load('gcn_metric_core_test',ROOT/'evaluation/pbmc_graph_perturbation/scripts/evaluate.py')


def tiny_model():
    import anndata as ad
    import scglue.models
    data={}
    for modality in ['rna','atac']:
        obj=ad.AnnData(X=np.ones((8,4),dtype=np.float32),var=pd.DataFrame(index=[modality+str(i) for i in range(4)]))
        obj.obsm['X_ref']=np.ones((8,100),dtype=np.float32)
        scglue.models.configure_dataset(obj,'NB',use_highly_variable=False,use_rep='X_ref')
        data[modality]=obj
    return scglue.models.SCGLUEModel(data,sorted(list(data['rna'].var_names)+list(data['atac'].var_names)),latent_dim=50,random_seed=2)


def test_actual_original_model_construction():
    import inspect
    import scglue.models
    from scglue.models.sc import GraphEncoder
    from scglue.models.nn import GraphConv
    assert 'graph_encoder' not in inspect.signature(scglue.models.SCGLUEModel.__init__).parameters
    assert 'gate_init' not in inspect.signature(scglue.models.SCGLUEModel.__init__).parameters
    assert 'lam_keep' not in inspect.signature(scglue.models.SCGLUEModel.compile).parameters
    model=tiny_model()
    assert type(model.net.g2v) is GraphEncoder
    assert type(model.net.g2v.conv) is GraphConv
    proof=common.verify_model(model)
    assert proof['model_seed']==2
    assert not proof['learned_edge_gates']


def test_rejects_any_learnable_gate_parameter():
    import torch
    model=tiny_model()
    model.net.g2v.register_parameter('gate_logits',torch.nn.Parameter(torch.zeros(1)))
    with pytest.raises(ValueError,match='gate/attention'):common.verify_model(model)


def test_graph_pairs_are_nested_and_preserve_signed_weighted_attributes():
    import networkx as nx
    graph=nx.DiGraph()
    for i in range(10):
        g,p='gene'+str(i),'peak'+str(i)
        weight=.2+.05*i;sign=-1 if i%2 else 1
        graph.add_edge(g,p,type='fwd',weight=weight,sign=sign)
        graph.add_edge(p,g,type='rev',weight=weight,sign=sign)
    for node in list(graph):graph.add_edge(node,node,type='loop',weight=1.,sign=1)
    last=set(graph.edges())
    for (condition,sub,metadata),count in zip(prepare.graph_conditions(graph),[10,7,5,2,1]):
        prepare.validate_preservation(graph,sub)
        assert metadata['resulting_relation_count']==count
        assert set(sub.edges())<=last
        assert sub.number_of_edges()==20+2*count
        last=set(sub.edges())
    assert graph.number_of_edges()==40


def test_all_15_prepared_manifest_entries_and_actual_graph_counts():
    import networkx as nx
    frame=common.validate_manifest()
    assert len(frame)==15
    assert set(frame.condition)==set(common.CONDITIONS)
    assert frame.graph_seed.eq(0).all()
    counts=[13493,10119,6746,3373,1349]
    for condition,count in zip(common.CONDITIONS,counts):
        group=frame[frame.condition==condition]
        assert set(group.model_seed)=={0,1,2}
        assert group.graph_path.nunique()==1
        graph=nx.read_graphml(group.graph_path.iloc[0])
        assert len(graph)==15205
        assert nx.number_of_selfloops(graph)==15205
        assert sum(d['type']=='fwd' for _,_,d in graph.edges(data=True))==count
        assert graph.number_of_edges()==15205+2*count


def test_original_runner_arguments_have_no_alternate_encoder_or_gate_options(tmp_path):
    row=SimpleNamespace(graph_path='/tmp/prior.graphml.gz',model_seed=1)
    args=train.runner_arguments(row,tmp_path,tmp_path,False)
    assert '--require-converge' in args
    assert '--graph-encoder' not in args
    assert not any('gate' in a or 'lam-keep' in a or 'gat-' in a for a in args)
    assert args[args.index('--lam-align')+1]=='0.05'
    assert args[args.index('--alt-dim')+1]=='100'
    assert '--require-converge' not in train.runner_arguments(row,tmp_path,tmp_path,True)


def test_gate_free_evaluation_does_not_read_gate_diagnostics(tmp_path,monkeypatch):
    import networkx as nx
    rng=np.random.RandomState(1)
    x=rng.normal(size=(12,50));y=x+.01
    ids=['cell'+str(i) for i in range(12)]
    for name,values in [('rna',x),('atac',y)]:pd.DataFrame(values,index=ids).to_csv(tmp_path/(name+'_latent.csv'),header=False)
    graph=nx.DiGraph();graph.add_nodes_from(['gene','peak'])
    pd.DataFrame(np.zeros((2,50)),index=['gene','peak']).to_csv(tmp_path/'feature_latent.csv',header=False)
    obs={m:pd.DataFrame({'cell_type':['A']*6+['B']*6},index=ids) for m in ['rna','atac']}
    args=SimpleNamespace(mode='full',cell_type='cell_type',cross_k=3,chunk_size=4,evaluation_seed=0,
                         lisi_perplexity=3,kbet_k=50,leiden_resolution=1.)
    row=SimpleNamespace(run_dir=str(tmp_path),condition='original',model_seed=0,graph_seed=0,task_id=0)
    def no_gates(*a,**kw):raise AssertionError('GCN attempted to read learned gates')
    monkeypatch.setattr(core,'gate_scores',no_gates)
    monkeypatch.setattr(core,'biological_scores',lambda x,l,m,a,s:s.add('graph_connectivity',1))
    result=core.evaluate_run(row,{'args':{'dim':50}},obs,{'verified':True},graph,{'node_count':2},[None,None],args,include_gates=False)
    assert not (tmp_path/'gate_diagnostics.yaml').exists()
    assert result['metrics']['foscttm']==0
    assert not any(name.startswith('gate_') for name in result['metrics'])
    assert result['metrics']['label_transfer_rna_to_atac_macro_f1']>0


def test_training_refused_without_slurm(monkeypatch):
    monkeypatch.delenv('SLURM_JOB_ID',raising=False)
    monkeypatch.setattr(sys,'argv',['train.py','--task-id','0'])
    with pytest.raises(SystemExit):train.main()


def test_smoke_preserves_original_balancing_settings_and_has_separate_stage_budgets():
    assert train.smoke_fit_limits('pretrain')['max_epochs']==50
    assert train.smoke_fit_limits('fine-tune')['max_epochs']==2
    assert common.SHARED['balance_cutoff']==.5
    assert common.SHARED['balance_power']==4.


def test_balance_audit_preserves_function_logger_and_rejects_nonfinite_weights():
    sentinel=object();runtime={}
    def original(data,**kw):
        # The real function accesses its logger through the replaced module name.
        assert runtime['function'].logger is sentinel
        data.obs['balancing_weight']=runtime['weights']
    original.logger=sentinel
    wrapped=train.checked_balancer(original)
    runtime.update(function=wrapped,weights=[1.,1.])
    data=SimpleNamespace(obs=pd.DataFrame(index=['a','b']))
    wrapped(data)
    np.testing.assert_array_equal(data.obs.balancing_weight,[1.,1.])
    runtime['weights']=[np.nan,np.nan]
    with pytest.raises(ValueError,match='nonfinite'):wrapped(data)
