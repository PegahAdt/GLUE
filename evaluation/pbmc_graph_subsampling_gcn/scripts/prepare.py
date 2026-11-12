#!/usr/bin/env python
"""Prepare exactly the previous PBMC relation subsets and frozen GCN inputs."""
import argparse
import json
import sys

import networkx as nx
import numpy as np
import pandas as pd

from common import (WORKTREE,EXPERIMENT,ORIGINAL,INPUT,PRIOR,GATED,DATASET,CONDITIONS,
                    FRACTIONS,SHARED,info,sha,save_json,edge_digest,original_sources,validate_manifest)

sys.path.insert(0,str(WORKTREE/'evaluation/workflow/scripts'))
from graph_perturbation import subsample_reciprocal_pairs


def graph_conditions(original):
    for condition,fraction in zip(CONDITIONS,FRACTIONS):
        if fraction==1:
            graph=original.copy();metadata={'graph_seed':0}
        else:
            graph,metadata=subsample_reciprocal_pairs(original,fraction,0)
        count=sum(u!=v and d['type']=='fwd' for u,v,d in graph.edges(data=True))
        metadata.update(original_node_count=len(original),original_relation_count=sum(
            u!=v and d['type']=='fwd' for u,v,d in original.edges(data=True)),resulting_relation_count=count)
        yield condition,graph,metadata


def validate_preservation(original,graph):
    if dict(original.nodes(data=True))!=dict(graph.nodes(data=True)):
        raise ValueError('Nodes/attributes changed')
    for u,v,d in graph.edges(data=True):
        if original.get_edge_data(u,v)!=d: raise ValueError('Retained edge attributes changed')
        if u!=v and not graph.has_edge(v,u): raise ValueError('Reciprocal relation missing')
    if {(u,v):d for u,v,d in original.edges(data=True) if u==v}!={
            (u,v):d for u,v,d in graph.edges(data=True) if u==v}:
        raise ValueError('Self-loops changed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-gated-models',action='store_true',help='Check actual saved GATED edge identities on CPU')
    args=parser.parse_args()
    EXPERIMENT.mkdir(parents=True,exist_ok=True)
    (EXPERIMENT/'graphs').mkdir(exist_ok=True)
    old=pd.read_csv(GATED/'manifest.csv')
    original=nx.read_graphml(PRIOR)
    # Also validates signed reciprocal schema at full retention.
    subsample_reciprocal_pairs(original,1.,0)
    evidence=[];graphs={};rows=[]
    for condition,graph,metadata in graph_conditions(original):
        validate_preservation(original,graph)
        for oldrow in old[old.condition==condition].itertuples(index=False):
            saved=info(oldrow.run_dir+'/run_info.yaml')
            if saved['graph_perturbation_metadata']!=metadata or saved['graph_seed']!=0:
                raise ValueError('GCN/GATED graph metadata differs: '+oldrow.run_dir)
            if saved['args']['prior']!=str(PRIOR): raise ValueError('Different original guidance graph')
            if any(saved['args'][k]!=v for k,v in SHARED.items()):
                raise ValueError('Shared GATED training settings differ')
        verified=False
        if args.verify_gated_models:
            # This process loads PBMC's package solely to inspect existing gates;
            # all original GCN construction/training happens in separate processes.
            sys.path.insert(0,str(WORKTREE))
            import scglue.models
            run=old[(old.condition==condition)&(old.model_seed==0)].iloc[0].run_dir
            model=scglue.models.load_model(run+'/final.dill')
            raw=model.get_graph_gates()
            source=np.asarray(model.vertices,dtype=str)[raw['source'].detach().cpu().numpy()]
            target=np.asarray(model.vertices,dtype=str)[raw['target'].detach().cpu().numpy()]
            if set(zip(source,target))!=set(graph.edges()):
                raise ValueError('Reconstructed subset differs from actual GATED checkpoint topology')
            del model,raw
            verified=True
        dest=EXPERIMENT/'graphs'/(condition+'.graphml.gz')
        if dest.exists():
            if edge_digest(nx.read_graphml(dest))!=edge_digest(graph): raise ValueError('Existing prepared graph differs')
        else: nx.write_graphml(graph,dest)
        loaded=nx.read_graphml(dest)
        if edge_digest(loaded)!=edge_digest(graph): raise ValueError('GraphML roundtrip changed relations/attributes')
        graphs[condition]=dict(path=str(dest),metadata=metadata,edge_identity_and_attributes_sha256=edge_digest(graph),
                              biological_pair_sha256=edge_digest(graph,True),gated_checkpoint_topology_verified=verified)
        evidence.append(dict(condition=condition,requested_fraction=FRACTIONS[CONDITIONS.index(condition)],
            biological_relation_count=metadata['resulting_relation_count'],node_count=len(graph),
            self_loop_count=nx.number_of_selfloops(graph),directed_edge_count=graph.number_of_edges(),
            realized_fraction=metadata['resulting_relation_count']/metadata['original_relation_count'],
            original_pair_overlap=metadata['resulting_relation_count'],graph_seed=0,
            gated_checkpoint_topology_verified=verified))
        for seed in range(3):
            rows.append(dict(task_id=len(rows),condition=condition,graph_perturbation='none' if condition=='original' else 'subsample',
                retain_fraction=FRACTIONS[CONDITIONS.index(condition)],graph_seed=0,model_seed=seed,graph_path=str(dest),
                run_dir=str(EXPERIMENT/'results'/DATASET/condition/'graph_seed:0'/('model_seed:'+str(seed)))))
    manifest=EXPERIMENT/'manifest.csv'
    selected=pd.DataFrame(rows)
    if manifest.exists() and not pd.read_csv(manifest).equals(selected):
        raise ValueError('Existing manifest differs; refusing overwrite')
    selected.to_csv(manifest,index=False)
    validate_manifest()
    pd.DataFrame(evidence).to_csv(EXPERIMENT/'graph_conditions.csv',index=False)
    save_json(EXPERIMENT/'validation/graph_verification.json',graphs)
    for row in rows:
        config=dict(shared=SHARED,model_seed=row['model_seed'],graph_seed=0,condition=row['condition'],
                    prior=row['graph_path'],architecture='original_glue_gcn',require_converge=True,
                    input_rna=str(INPUT/'rna.h5ad'),input_atac=str(INPUT/'atac.h5ad'))
        save_json(EXPERIMENT/'configurations'/('task_{}.json'.format(row['task_id'])),config)
    frozen=dict(original_repository=str(ORIGINAL),original_source_sha256=original_sources(),
        perturbation_code_sha256=sha(WORKTREE/'evaluation/workflow/scripts/graph_perturbation.py'),
        original_prior_sha256=sha(PRIOR),manifest_sha256=sha(manifest),shared_training_settings=SHARED,
        raw_inputs={str(INPUT/(m+'.h5ad')):dict(size=(INPUT/(m+'.h5ad')).stat().st_size,
                    mtime_ns=(INPUT/(m+'.h5ad')).stat().st_mtime_ns) for m in ['rna','atac']},
        graph_file_sha256={g['path']:sha(g['path']) for g in graphs.values()},
        graph_seed=0,baseline_policy='Train fresh original baselines for all three seeds; historical preprocessing/source snapshot not frozen',
        model_seeds=[0,1,2],n_runs=15)
    lock=EXPERIMENT/'validation/frozen_inputs.json'
    if lock.exists() and json.loads(lock.read_text())!=frozen: raise ValueError('Existing frozen configuration differs')
    save_json(lock,frozen)
    save_json(EXPERIMENT/'validation/preflight.json',dict(status='passed',manifest_entries=15,
               conditions=5,graph_seed=0,actual_gated_model_topology_verified=args.verify_gated_models))
    print(pd.DataFrame(evidence).to_string(index=False),flush=True)
    print('Verified 15 entries; prepared graph nodes, loops, attributes and reciprocal pairs preserved.',flush=True)


if __name__=='__main__':main()
