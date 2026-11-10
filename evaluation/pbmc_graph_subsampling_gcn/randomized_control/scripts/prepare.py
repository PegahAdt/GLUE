"""Prove exact GATED graph equivalence before creating any training manifest."""
import json
import hashlib
import sys
import types
from collections import Counter
import networkx as nx
import numpy as np
import pandas as pd
from common import *


def exact_equal(a, b):
    if dict(a.nodes(data=True)) != dict(b.nodes(data=True)) or a.graph != b.graph:
        raise ValueError('Graph/node attributes differ')
    if {(u,v):d for u,v,d in a.edges(data=True)} != {(u,v):d for u,v,d in b.edges(data=True)}:
        raise ValueError('Exact directed edge identities or attributes differ')


def completed_evaluator_source(config):
    path=GATED/'scripts/evaluate.py'
    source=path.read_text()
    # The existing GCN experiment added only an optional gate-diagnostics switch.
    # Undo that precise addition, then require the completed report's exact hash.
    restored=source.replace(', include_gates=True):', '):')
    start=restored.index('    if include_gates:\n');stop=restored.index('    meta = dict(',start)
    restored=restored[:start]+''.join(line[4:] if line.startswith('    ') else line for line in
        restored[start+len('    if include_gates:\n'):stop].splitlines(keepends=True))+restored[stop:]
    expected=config['source_hashes'][str(path.relative_to(WORKTREE))]
    if hashlib.sha256(restored.encode()).hexdigest()!=expected:
        raise ValueError('Shared evaluator has changes beyond the known gate-only switch')
    return restored,dict(completed_evaluator_sha256=expected,current_evaluator_sha256=sha(path),
        only_change='Optional include_gates=True switch around the unchanged gate diagnostics block',
        exact_completed_source_restored=True)


def preservation(original, graph):
    if dict(original.nodes(data=True)) != dict(graph.nodes(data=True)):
        raise ValueError('Nodes/attributes changed')
    for method in ['in_degree','out_degree']:
        if dict(getattr(original,method)()) != dict(getattr(graph,method)()):
            raise ValueError('Per-node degrees changed')
    if {(u,v):d for u,v,d in original.edges(data=True) if u==v} != {
            (u,v):d for u,v,d in graph.edges(data=True) if u==v}:
        raise ValueError('Self-loops changed')
    genes={u for u,v,d in original.edges(data=True) if d['type']=='fwd'}
    peaks={v for u,v,d in original.edges(data=True) if d['type']=='fwd'}
    for u,v,d in graph.edges(data=True):
        if u==v: continue
        if (u not in genes or v not in peaks) if d['type']=='fwd' else (u not in peaks or v not in genes):
            raise ValueError('Bipartite structure changed')
        reverse=graph.get_edge_data(v,u)
        if reverse is None or reverse['type'] != ('rev' if d['type']=='fwd' else 'fwd'):
            raise ValueError('Reciprocal semantics differ')
        if any(d[k]!=reverse[k] for k in ['weight','sign']):
            raise ValueError('Reciprocal signed/weighted semantics differ')
    attrs=lambda g: Counter(json.dumps(d,sort_keys=True) for u,v,d in g.edges(data=True))
    if attrs(original)!=attrs(graph): raise ValueError('Complete edge attribute multiset changed')


def main():
    base.verify_freeze()
    config=json.loads((GATED/'reports/full/evaluation_config.json').read_text())
    if json.loads((GATED/'reports/full/status.json').read_text())['status']!='complete':
        raise ValueError('GATED full evaluation is not complete')
    if config['original_graph_sha256']!={str(PRIOR):sha(PRIOR)}:
        raise ValueError('Original graph differs from completed GATED evaluation')
    source=WORKTREE/'evaluation/workflow/scripts/graph_perturbation.py'
    if sha(source)!=config['source_hashes'][str(source.relative_to(WORKTREE))]:
        raise ValueError('Randomization implementation differs from completed GATED report')
    sys.path.insert(0,str(source.parent))
    from graph_perturbation import randomize_topology, _relations
    original=nx.read_graphml(PRIOR)
    graph, metadata=randomize_topology(original,0,swap_multiplier=10.)
    metadata.update(original_node_count=len(original),original_relation_count=len(_relations(original)),
                    resulting_relation_count=len(_relations(graph)))
    if not metadata['completed'] or metadata['accepted_swaps']!=134930:
        raise ValueError('Randomization incomplete or incorrect swap count')
    preservation(original,graph)
    sys.path.insert(0,str(GATED/'scripts'))
    restored,source_proof=completed_evaluator_source(config)
    archive=EXPERIMENT/'validation/completed_gated_evaluate.py'
    archive.parent.mkdir(parents=True,exist_ok=True)
    if archive.exists() and archive.read_text()!=restored: raise ValueError('Archived completed evaluator differs')
    if not archive.exists():archive.write_text(restored)
    gated_evaluator=types.ModuleType('completed_gated_evaluator')
    gated_evaluator.__file__=str(GATED/'scripts/evaluate.py')
    exec(compile(restored,gated_evaluator.__file__,'exec'),gated_evaluator.__dict__)
    sys.path.insert(0,str(WORKTREE))
    import scglue.models
    proofs=[]
    runs=pd.read_csv(GATED/'manifest.csv')
    for row in runs[runs.condition=='randomized'].itertuples(index=False):
        saved=info(Path(row.run_dir)/'run_info.yaml')
        if saved['graph_perturbation_metadata']!=metadata:
            raise ValueError('GATED randomization parameters/metadata differ')
        if saved['args']['prior']!=str(PRIOR) or saved['graph_seed']!=0 or saved['graph_swap_multiplier']!=10.:
            raise ValueError('GATED graph inputs differ')
        if any(saved['args'][k]!=v for k,v in SHARED.items()): raise ValueError('GATED shared settings differ')
        for m in ['rna','atac']:
            if Path(saved['args']['input_'+m]).resolve()!=(INPUT/(m+'.h5ad')).resolve():
                raise ValueError('GATED preprocessing inputs differ')
        reconstructed,_=gated_evaluator.reconstruct_graph(saved)
        exact_equal(graph,reconstructed)
        checkpoint=Path(row.run_dir)/'final.dill'
        model=scglue.models.load_model(checkpoint)
        raw=model.get_graph_gates()
        vertices=np.asarray(model.vertices,dtype=str)
        endpoints=list(zip(vertices[raw['source'].cpu().numpy()],vertices[raw['target'].cpu().numpy()]))
        if len(endpoints)!=graph.number_of_edges() or set(endpoints)!=set(graph.edges()):
            raise ValueError('Actual GATED checkpoint directed edge identities differ')
        if set(model.vertices)!=set(graph): raise ValueError('GATED checkpoint node identities differ')
        archived=next(x for x in config['run_input_sha256'] if str(checkpoint) in x)
        if sha(checkpoint)!=archived[str(checkpoint)] or sha(Path(row.run_dir)/'run_info.yaml')!=archived[str(Path(row.run_dir)/'run_info.yaml')]:
            raise ValueError('GATED checkpoint/provenance changed since completed evaluation')
        proofs.append(dict(model_seed=int(row.model_seed),checkpoint=str(checkpoint),checkpoint_sha256=sha(checkpoint),
            exact_checkpoint_edge_identities=True,exact_reconstructed_edge_attributes=True,
            reconstructed_edge_identity_and_attributes_sha256=edge_digest(reconstructed)))
        del model,raw
    if sorted(p['model_seed'] for p in proofs)!=[0,1,2]: raise ValueError('Missing GATED randomized seeds')
    dest=EXPERIMENT/'graphs/randomized.graphml.gz'
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists(): exact_equal(graph,nx.read_graphml(dest))
    else: nx.write_graphml(graph,dest)
    exact_equal(graph,nx.read_graphml(dest))
    evidence=dict(status='passed',metadata=metadata,path=str(dest),
        metric_source_equivalence=source_proof,
        edge_identity_and_attributes_sha256=edge_digest(graph),
        biological_pair_sha256=edge_digest(graph,True),gated_checkpoints=proofs,
        node_count=len(graph),directed_edge_count=graph.number_of_edges(),self_loop_count=nx.number_of_selfloops(graph),
        nodes_and_attributes_preserved=True,self_loops_and_attributes_preserved=True,
        per_node_nonloop_in_out_degree_preserved=True,bipartite_and_reciprocal_preserved=True,
        signed_weighted_semantics_preserved=True,complete_attribute_multiset_preserved=True,
        original_prior_sha256=sha(PRIOR),perturbation_code_sha256=sha(source),
        attribute_evidence='Complete attributes reconstructed using the exact hash-verified GATED evaluator, prior, seeded algorithm and saved parameters; checkpoints retain endpoint identities, not provenance attributes such as dist/id. PBMC weight=1 and sign=1 are uniform and carried unchanged.',
        protected_files_sha256={str(p):sha(p) for p in [BASE/'manifest.csv',BASE/'validation/frozen_inputs.json',BASE/'submission.json']+list((BASE/'scripts').glob('*.py'))+list(BASE.glob('*.sbatch'))})
    save_json(EXPERIMENT/'validation/graph_verification.json',{'randomized':evidence})
    rows=[dict(task_id=s,condition='randomized',graph_perturbation='randomize',retain_fraction=1.,graph_seed=0,
        model_seed=s,graph_path=str(dest),run_dir=str(BASE/'results'/DATASET/'randomized'/'graph_seed:0'/('model_seed:'+str(s)))) for s in range(3)]
    for name,frame in [('manifest.csv',pd.DataFrame(rows)),('combined_manifest.csv',pd.concat([
            base.validate_manifest(),pd.DataFrame([dict(r,task_id=r['task_id']+15) for r in rows])],ignore_index=True))]:
        path=EXPERIMENT/name
        if path.exists() and not pd.read_csv(path).equals(frame): raise ValueError('Refuse manifest overwrite')
        if not path.exists(): frame.to_csv(path,index=False)
        validate_manifest(path)
    for row in rows:
        save_json(EXPERIMENT/'configurations'/('task_'+str(row['task_id'])+'.json'),dict(row,shared=SHARED,
            input_rna=str(INPUT/'rna.h5ad'),input_atac=str(INPUT/'atac.h5ad'),architecture='original_glue_gcn',require_converge=True))
    print(json.dumps(evidence,indent=2),flush=True)


if __name__=='__main__': main()
