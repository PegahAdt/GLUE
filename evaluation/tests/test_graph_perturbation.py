"""Synthetic invariant tests requiring no GLUE model or PBMC data."""

import copy
import importlib.util
import math
import pathlib
import random
from collections import Counter

import networkx as nx
import numpy as np
import pytest


HELPER = pathlib.Path(__file__).parents[1] / "workflow/scripts/graph_perturbation.py"
SPEC = importlib.util.spec_from_file_location("graph_perturbation", HELPER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
subsample_reciprocal_pairs = MODULE.subsample_reciprocal_pairs
randomize_topology = MODULE.randomize_topology


@pytest.fixture
def graph():
    result = nx.DiGraph(experiment={"labels": ["synthetic"]})
    # Irregular degrees, unused features with loops, and a truly isolated node.
    pairs = [
        ("g0", "p0"), ("g0", "p1"), ("g0", "p2"),
        ("g1", "p1"), ("g1", "p3"),
        ("g2", "p2"), ("g2", "p4"), ("g2", "p5"),
        ("g3", "p3"), ("g4", "p4"), ("g5", "p5"),
    ]
    for prefix, modality in [("g", "gene"), ("p", "peak")]:
        for i in range(7):
            node = prefix + str(i)
            result.add_node(node, modality=modality, annotations={"values": [i]})
            result.add_edge(node, node, weight=1.0, sign=1, type="loop", id="0")
    result.add_node("isolated", annotations={"values": []})
    for i, (gene, peak) in enumerate(pairs):
        attrs = dict(weight=1.0, sign=1, dist=i, id="0", provenance={"slot": [i]})
        result.add_edge(gene, peak, type="fwd", **copy.deepcopy(attrs))
        result.add_edge(peak, gene, type="rev", **copy.deepcopy(attrs))
    return result


def snapshot(graph):
    return copy.deepcopy((graph.graph, dict(graph.nodes(data=True)), dict(graph.edges)))


def relations(graph):
    return {(u, v) for u, v, attrs in graph.edges(data=True) if attrs["type"] == "fwd"}


def nonloop_degrees(graph):
    return {
        node: (graph.in_degree(node) - int(graph.has_edge(node, node)),
               graph.out_degree(node) - int(graph.has_edge(node, node)))
        for node in graph
    }


def check_invariants(original, result):
    assert type(result) is nx.DiGraph
    assert set(result) == set(original)
    assert dict(result.nodes(data=True)) == dict(original.nodes(data=True))
    assert result.graph == original.graph
    original_loops = {(u, v): attrs for u, v, attrs in nx.selfloop_edges(original, data=True)}
    result_loops = {(u, v): attrs for u, v, attrs in nx.selfloop_edges(result, data=True)}
    assert result_loops == original_loops
    forward_list = [(u, v) for u, v, attrs in result.edges(data=True) if attrs["type"] == "fwd"]
    assert len(forward_list) == len(set(forward_list))
    assert result.number_of_edges() == len(result_loops) + 2 * len(forward_list)
    assert len(list(result.edges())) == len(set(result.edges()))
    for u, v, attrs in result.edges(data=True):
        assert math.isfinite(attrs["weight"]) and 0 < attrs["weight"] <= 1
        assert attrs["sign"] in {-1, 1}
        if u == v:
            continue
        assert result.has_edge(v, u)
        reverse = result[v][u]
        assert reverse["weight"] == attrs["weight"]
        assert reverse["sign"] == attrs["sign"]
        if attrs["type"] == "fwd":
            assert result.nodes[u]["modality"] == "gene"
            assert result.nodes[v]["modality"] == "peak"
            assert reverse["type"] == "rev"
        else:
            assert attrs["type"] == "rev"
            assert result.nodes[u]["modality"] == "peak"
            assert result.nodes[v]["modality"] == "gene"
            assert reverse["type"] == "fwd"


@pytest.mark.parametrize("fraction, expected", [
    (1.0, 11), (0.75, 8), (0.5, 5), (0.25, 2), (0.10, 1), (0.0, 0)
])
def test_subsampling_counts_attributes_and_invariants(graph, fraction, expected):
    before = snapshot(graph)
    result, metadata = subsample_reciprocal_pairs(graph, fraction, 7)
    assert snapshot(graph) == before
    check_invariants(graph, result)
    assert len(relations(result)) == expected
    assert relations(result) <= relations(graph)
    for u, v, attrs in result.edges(data=True):
        assert attrs == graph[u][v]
    assert metadata == {
        "original_relation_count": 11,
        "retained_relation_count": expected,
        "requested_fraction": fraction,
        "realized_fraction": expected / 11,
        "graph_seed": 7,
    }


def test_subsampling_nested_reproducible_and_seed_dependent(graph):
    outputs = [subsample_reciprocal_pairs(graph, f, 13)[0] for f in [0.10, 0.25, 0.5, 0.75, 1.0]]
    assert all(relations(a) <= relations(b) for a, b in zip(outputs, outputs[1:]))
    first, first_meta = subsample_reciprocal_pairs(graph, 0.5, 13)
    repeat, repeat_meta = subsample_reciprocal_pairs(graph, 0.5, 13)
    assert snapshot(first) == snapshot(repeat)
    assert first_meta == repeat_meta
    alternatives = {frozenset(relations(subsample_reciprocal_pairs(graph, 0.5, s)[0])) for s in range(8)}
    assert len(alternatives) > 1


@pytest.mark.parametrize("seed", [0, 1, 7])
def test_randomization_degrees_relations_attributes_and_diagnostics(graph, seed):
    before = snapshot(graph)
    result, metadata = randomize_topology(graph, seed, n_swaps=55)
    assert snapshot(graph) == before
    check_invariants(graph, result)
    assert nonloop_degrees(result) == nonloop_degrees(graph)
    assert len(relations(result)) == len(relations(graph)) == 11
    for kind in ("fwd", "rev"):
        original_attrs = Counter(
            repr(sorted(a.items())) for _, _, a in graph.edges(data=True) if a["type"] == kind
        )
        result_attrs = Counter(
            repr(sorted(a.items())) for _, _, a in result.edges(data=True) if a["type"] == kind
        )
        assert result_attrs == original_attrs
    overlap = len(relations(graph) & relations(result))
    assert metadata["relation_count"] == 11
    assert metadata["graph_seed"] == seed
    assert metadata["accepted_swaps"] == metadata["requested_swaps"] == 55
    assert 55 <= metadata["attempted_swaps"] <= metadata["max_attempts"]
    assert metadata["completed"]
    assert metadata["termination_reason"] == "requested_swaps_reached"
    assert metadata["original_relation_overlap"] == overlap
    assert metadata["original_relation_overlap_fraction"] == overlap / 11
    assert relations(result) != relations(graph)


def test_randomization_reproducibility_seed_and_insertion_order(graph):
    first, first_meta = randomize_topology(graph, 31, n_swaps=55)
    repeat, repeat_meta = randomize_topology(graph, 31, n_swaps=55)
    assert snapshot(first) == snapshot(repeat)
    assert first_meta == repeat_meta
    alternatives = {frozenset(relations(randomize_topology(graph, s, n_swaps=55)[0])) for s in range(8)}
    assert len(alternatives) > 1
    reordered = nx.DiGraph(**copy.deepcopy(graph.graph))
    reordered.add_nodes_from(reversed(list(copy.deepcopy(graph).nodes(data=True))))
    reordered.add_edges_from(reversed(list(copy.deepcopy(graph).edges(data=True))))
    for operation, kwargs in [(subsample_reciprocal_pairs, {"retain_fraction": 0.5}),
                              (randomize_topology, {"n_swaps": 55})]:
        original_result, original_meta = operation(graph, graph_seed=31, **kwargs)
        reordered_result, reordered_meta = operation(reordered, graph_seed=31, **kwargs)
        assert snapshot(original_result) == snapshot(reordered_result)
        assert original_meta == reordered_meta


@pytest.mark.parametrize("operation", ["subsample", "randomize"])
def test_local_rng_and_independent_nested_attribute_copies(graph, operation):
    python_state, numpy_state = random.getstate(), np.random.get_state()
    before = snapshot(graph)
    if operation == "subsample":
        result, _ = subsample_reciprocal_pairs(graph, 0.75, 42)
    else:
        result, _ = randomize_topology(graph, 42, n_swaps=22)
    assert random.getstate() == python_state
    after_numpy = np.random.get_state()
    assert after_numpy[0] == numpy_state[0]
    assert np.array_equal(after_numpy[1], numpy_state[1])
    assert after_numpy[2:] == numpy_state[2:]
    result.graph["experiment"]["labels"].append("changed")
    result.nodes["g0"]["annotations"]["values"].append(999)
    result["g0"]["g0"]["weight"] = 0.5
    gene, peak = next(iter(relations(result)))
    result[gene][peak]["provenance"]["slot"].append(999)
    assert snapshot(graph) == before


@pytest.mark.parametrize("operation", ["subsample", "randomize"])
def test_graph_seed_is_independent_of_global_seeds(graph, operation):
    python_state, numpy_state = random.getstate(), np.random.get_state()
    outputs = []
    try:
        for global_seed in [1, 999]:
            random.seed(global_seed)
            np.random.seed(global_seed)
            if operation == "subsample":
                result, metadata = subsample_reciprocal_pairs(graph, 0.5, 42)
            else:
                result, metadata = randomize_topology(graph, 42, n_swaps=22)
            outputs.append((snapshot(result), metadata))
        assert outputs[0] == outputs[1]
    finally:
        random.setstate(python_state)
        np.random.set_state(numpy_state)


@pytest.mark.parametrize("operation", ["subsample", "randomize"])
def test_original_node_identifiers_are_preserved(graph, operation):
    # A full deepcopy(graph) would replace this identity-based isolated node.
    marker = object()
    graph.add_node(marker)
    if operation == "subsample":
        result, _ = subsample_reciprocal_pairs(graph, 0.5, 42)
    else:
        result, _ = randomize_topology(graph, 42, n_swaps=22)
    assert set(result) == set(graph)
    assert marker in result
    assert result.degree(marker) == 0


def test_heterogeneous_weights_signs_are_carried_together(graph):
    for i, (gene, peak) in enumerate(sorted(relations(graph))):
        for u, v in [(gene, peak), (peak, gene)]:
            graph[u][v].update(weight=(i + 1) / 11, sign=-1 if i % 2 else 1)
    result, metadata = randomize_topology(graph, 17, n_swaps=55)
    check_invariants(graph, result)
    assert metadata["completed"]
    original_attributes = Counter((a["weight"], a["sign"]) for _, _, a in graph.edges(data=True))
    result_attributes = Counter((a["weight"], a["sign"]) for _, _, a in result.edges(data=True))
    assert result_attributes == original_attributes
    assert nonloop_degrees(result) == nonloop_degrees(graph)
    for gene, peak in relations(result):
        assert result[gene][peak]["provenance"] == result[peak][gene]["provenance"]


def test_multiplier_rounding_and_zero_swaps(graph):
    _, metadata = randomize_topology(graph, 0, swap_multiplier=0.25)
    assert metadata["requested_swaps"] == metadata["accepted_swaps"] == 3
    for kwargs in [{"n_swaps": 0}, {"swap_multiplier": 0}]:
        result, metadata = randomize_topology(graph, 0, **kwargs)
        assert snapshot(result) == snapshot(graph)
        assert metadata["accepted_swaps"] == metadata["attempted_swaps"] == 0
        assert metadata["original_relation_overlap_fraction"] == 1.0
        assert metadata["completed"]
    _, metadata = randomize_topology(graph, 0, n_swaps=1, swap_multiplier=100)
    assert metadata["requested_swaps"] == 1


def test_attempt_limit_reports_partial_result(graph):
    result, metadata = randomize_topology(graph, 0, n_swaps=55, max_attempts=3)
    check_invariants(graph, result)
    assert nonloop_degrees(result) == nonloop_degrees(graph)
    assert not metadata["completed"]
    assert metadata["attempted_swaps"] == 3
    assert metadata["accepted_swaps"] <= 3
    assert metadata["termination_reason"] == "max_attempts_reached"


def test_unswappable_complete_bipartite_graph_is_bounded(graph):
    dense = copy.deepcopy(graph)
    for gene in ["g0", "g1"]:
        for peak in ["p0", "p1"]:
            dense.add_edge(gene, peak, weight=1.0, sign=1, type="fwd")
            dense.add_edge(peak, gene, weight=1.0, sign=1, type="rev")
    dense = dense.subgraph(["g0", "g1", "p0", "p1"]).copy()
    result, metadata = randomize_topology(dense, 0, n_swaps=1, max_attempts=20)
    assert snapshot(result) == snapshot(dense)
    assert metadata["attempted_swaps"] == 20
    assert metadata["accepted_swaps"] == 0
    assert not metadata["completed"]


@pytest.mark.parametrize("count", [0, 1])
def test_zero_or_one_relation(graph, count):
    small, _ = subsample_reciprocal_pairs(graph, count / 11, 0)
    assert len(relations(small)) == count
    result, metadata = randomize_topology(small, 0, n_swaps=1)
    assert snapshot(result) == snapshot(small)
    assert not metadata["completed"]
    assert metadata["attempted_swaps"] == metadata["accepted_swaps"] == 0
    assert metadata["original_relation_overlap_fraction"] == 1.0
    if count == 0:
        result, sub_meta = subsample_reciprocal_pairs(small, 0.5, 0)
        assert snapshot(result) == snapshot(small)
        assert sub_meta["realized_fraction"] == 1.0


@pytest.mark.parametrize("fraction", [-0.1, 1.1, float("nan"), float("inf"), True, "0.5"])
def test_invalid_fractions(graph, fraction):
    with pytest.raises(ValueError):
        subsample_reciprocal_pairs(graph, fraction, 0)


@pytest.mark.parametrize("kwargs", [
    {"n_swaps": -1}, {"n_swaps": 1.5}, {"n_swaps": True},
    {"swap_multiplier": -1}, {"swap_multiplier": float("nan")},
    {"swap_multiplier": float("inf")}, {"max_attempts": -1},
    {"max_attempts": 1.5}, {"graph_seed": 1.5}, {"graph_seed": True},
])
def test_invalid_randomization_parameters(graph, kwargs):
    options = {"graph_seed": 0}
    options.update(kwargs)
    with pytest.raises(ValueError):
        randomize_topology(graph, **options)


@pytest.mark.parametrize("corruption", ["undirected", "multigraph", "missing_reverse", "bad_type",
                                        "overlapping_partitions", "bad_weight", "bad_sign",
                                        "nan_weight", "missing_weight", "mismatched_reverse"])
@pytest.mark.parametrize("operation", ["subsample", "randomize"])
def test_invalid_graphs_fail_without_mutation(graph, corruption, operation):
    gene, peak = sorted(relations(graph))[0]
    if corruption == "undirected":
        graph = nx.Graph(graph)
    elif corruption == "multigraph":
        graph = nx.MultiDiGraph(graph)
        graph.add_edge(gene, peak, **copy.deepcopy(graph[gene][peak][0]))
    elif corruption == "missing_reverse":
        graph.remove_edge(peak, gene)
    elif corruption == "bad_type":
        graph[gene][peak]["type"] = "unknown"
    elif corruption == "overlapping_partitions":
        graph.add_edge("p0", "g1", weight=1.0, sign=1, type="fwd")
        graph.add_edge("g1", "p0", weight=1.0, sign=1, type="rev")
    elif corruption == "bad_weight":
        graph[gene][peak]["weight"] = 0
    elif corruption == "nan_weight":
        graph[gene][peak]["weight"] = float("nan")
    elif corruption == "bad_sign":
        graph[gene][peak]["sign"] = 0
    elif corruption == "missing_weight":
        del graph[gene][peak]["weight"]
    else:
        graph[peak][gene]["weight"] = 0.5
    # repr also compares the deliberately introduced NaN without NaN != NaN.
    before = repr(snapshot(graph))
    with pytest.raises(ValueError):
        if operation == "subsample":
            subsample_reciprocal_pairs(graph, 0.5, 0)
        else:
            randomize_topology(graph, 0, n_swaps=1)
    assert repr(snapshot(graph)) == before
