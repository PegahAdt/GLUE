"""Perturb reciprocal gene--peak guidance graphs without changing their nodes.

Both operations return ``(graph, metadata)`` and leave the input untouched,
including nested attributes. They use only a local ``random.Random`` instance;
neither Python's nor NumPy's global RNG state is changed. Node IDs must be
mutually orderable, as the string IDs loaded from GraphML are. Sorting relations
before sampling makes results independent of graph insertion order.

The supported input is a simple DiGraph with paired gene->peak ``type='fwd'``
and peak->gene ``type='rev'`` edges. Reciprocal weight/sign values must agree.
Self-loops have ``type='loop'``. Nodes with only loops, or no edges, are allowed.
"""

import copy
import math
import random
from numbers import Integral, Real
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx


def _integer(value: int, name: str, nonnegative: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("{} must be an integer".format(name))
    result = int(value)
    if nonnegative and result < 0:
        raise ValueError("{} must be nonnegative".format(name))
    return result


def _finite_real(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("{} must be a finite real number".format(name))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("{} must be a finite real number".format(name))
    return result


def _relations(graph: nx.DiGraph) -> List[Tuple[Any, Any]]:
    """Validate the schema and infer partitions from forward edge endpoints."""
    if not isinstance(graph, nx.DiGraph) or graph.is_multigraph():
        raise ValueError("graph must be a simple NetworkX DiGraph")
    relations = []
    genes, peaks = set(), set()
    for u, v, attrs in graph.edges(data=True):
        weight = _finite_real(attrs.get("weight"), "edge weight")
        if not 0 < weight <= 1:
            raise ValueError("edge weight must be in (0, 1]")
        sign = _finite_real(attrs.get("sign"), "edge sign")
        if sign not in (-1, 1):
            raise ValueError("edge sign must be -1 or 1")
        edge_type = attrs.get("type")
        if u == v:
            if edge_type != "loop":
                raise ValueError("self-loops must have type='loop'")
            continue
        if edge_type not in ("fwd", "rev"):
            raise ValueError("non-loop edges must have type='fwd' or 'rev'")
        reverse = graph.get_edge_data(v, u)
        expected_type = "rev" if edge_type == "fwd" else "fwd"
        if reverse is None or reverse.get("type") != expected_type:
            raise ValueError("each relation must have reciprocal fwd/rev edges")
        if any(attrs[key] != reverse.get(key) for key in ("weight", "sign")):
            raise ValueError("reciprocal weight/sign attributes must agree")
        if edge_type == "fwd":
            genes.add(u)
            peaks.add(v)
            relations.append((u, v))
    if genes & peaks:
        raise ValueError("gene and peak partitions must be disjoint")
    try:
        return sorted(relations)
    except TypeError as exc:
        raise ValueError("node IDs must be mutually orderable") from exc


def _copy_graph(graph: nx.DiGraph) -> nx.DiGraph:
    """Copy attributes deeply while retaining the original node identifiers.

    Deep-copying the whole graph could replace identity-based node objects,
    violating exact node-set preservation even though strings are unaffected.
    """
    result = nx.DiGraph()
    result.graph.update(copy.deepcopy(graph.graph))
    result.add_nodes_from(
        (node, copy.deepcopy(attrs)) for node, attrs in graph.nodes(data=True)
    )
    result.add_edges_from(
        (u, v, copy.deepcopy(attrs)) for u, v, attrs in graph.edges(data=True)
    )
    return result


def subsample_reciprocal_pairs(
    graph: nx.DiGraph, retain_fraction: float, graph_seed: int
) -> Tuple[nx.DiGraph, Dict[str, Any]]:
    """Uniformly retain a fixed number of reciprocal biological relations.

    The count is exactly ``floor(float(retain_fraction) * N)``, where N is
    the original relation count and multiplication uses Python floating-point
    arithmetic. Fractions must be finite and in [0, 1]. A seeded permutation
    of the sorted original relations supplies prefixes, so smaller fractions
    are nested subsets for the same original graph and graph_seed.

    Original node identifiers are retained; graph/node/edge attributes are
    deep-copied, including self-loop attributes. For an input with no
    relations, realized_fraction is defined as 1.0.
    """
    fraction = _finite_real(retain_fraction, "retain_fraction")
    if not 0 <= fraction <= 1:
        raise ValueError("retain_fraction must be in [0, 1]")
    seed = _integer(graph_seed, "graph_seed")
    relations = _relations(graph)
    original_count = len(relations)
    retained_count = math.floor(fraction * original_count)
    random.Random(seed).shuffle(relations)
    result = _copy_graph(graph)
    for gene, peak in relations[retained_count:]:
        result.remove_edge(gene, peak)
        result.remove_edge(peak, gene)
    return result, {
        "original_relation_count": original_count,
        "retained_relation_count": retained_count,
        "requested_fraction": fraction,
        "realized_fraction": retained_count / original_count if original_count else 1.0,
        "graph_seed": seed,
    }


def randomize_topology(
    graph: nx.DiGraph,
    graph_seed: int,
    *,
    swap_multiplier: float = 10.0,
    n_swaps: Optional[int] = None,
    max_attempts: Optional[int] = None
) -> Tuple[nx.DiGraph, Dict[str, Any]]:
    """Randomize relations by degree-preserving bipartite reciprocal swaps.

    Two uniformly chosen distinct relation slots (g1, p1), (g2, p2) become
    (g1, p2), (g2, p1). Shared genes/peaks and existing proposed relations
    are rejected. Both directions are updated together. All nodes and loops,
    relation count, and each node's non-loop in/out-degree remain unchanged.

    Request n_swaps successful swaps, or otherwise ceil(swap_multiplier * N).
    An explicit n_swaps overrides swap_multiplier. By default, attempts are
    capped at 100 times the requested count. A partial result is returned if
    this limit is exhausted or fewer than two relations exist: callers must
    check metadata['completed'] before using it as a randomized control.

    Each slot carries both original attribute dictionaries to its new
    endpoints. This preserves the joint weight/sign distribution and schema,
    including heterogeneous weights/signs. Weighted degree at individual
    peaks need not be preserved for heterogeneous weights. For PBMC's uniform
    unit weights, weighted degrees are preserved as well.

    IMPORTANT: retained dist values are provenance only after rewiring and
    are NOT biologically meaningful distances for the new endpoints.
    run_GLUE consumes weight/sign, not dist. GraphML id is also carried as
    metadata, not used as a unique relation identifier.

    Swaps need not preserve components or eliminate all original relations;
    overlap is measured on biological pairs, excluding all self-loops.
    For zero relations, overlap_fraction is defined as 1.0.
    """
    seed = _integer(graph_seed, "graph_seed")
    relations = _relations(graph)
    count = len(relations)
    if n_swaps is None:
        multiplier = _finite_real(swap_multiplier, "swap_multiplier")
        if multiplier < 0:
            raise ValueError("swap_multiplier must be nonnegative")
        target = math.ceil(multiplier * count)
    else:
        target = _integer(n_swaps, "n_swaps", nonnegative=True)
    limit = 100 * target if max_attempts is None else _integer(
        max_attempts, "max_attempts", nonnegative=True
    )
    rng = random.Random(seed)
    original_relations = set(relations)
    current_relations = set(relations)
    result = _copy_graph(graph)
    attempted = accepted = 0
    while count >= 2 and accepted < target and attempted < limit:
        attempted += 1
        first, second = rng.sample(range(count), 2)
        gene1, peak1 = relations[first]
        gene2, peak2 = relations[second]
        if gene1 == gene2 or peak1 == peak2:
            continue
        new1, new2 = (gene1, peak2), (gene2, peak1)
        if new1 in current_relations or new2 in current_relations:
            continue

        # Carry complete reciprocal attribute pairs; dist is provenance only.
        fwd1, rev1 = result[gene1][peak1], result[peak1][gene1]
        fwd2, rev2 = result[gene2][peak2], result[peak2][gene2]
        result.remove_edges_from([
            (gene1, peak1), (peak1, gene1), (gene2, peak2), (peak2, gene2)
        ])
        result.add_edges_from([
            (gene1, peak2, fwd1), (peak2, gene1, rev1),
            (gene2, peak1, fwd2), (peak1, gene2, rev2)
        ])
        current_relations.remove((gene1, peak1))
        current_relations.remove((gene2, peak2))
        current_relations.update((new1, new2))
        relations[first], relations[second] = new1, new2
        accepted += 1

    overlap = len(original_relations & current_relations)
    completed = accepted == target
    return result, {
        "relation_count": count,
        "graph_seed": seed,
        "requested_swaps": target,
        "max_attempts": limit,
        "attempted_swaps": attempted,
        "accepted_swaps": accepted,
        "completed": completed,
        "termination_reason": (
            "requested_swaps_reached" if completed else
            "fewer_than_two_relations" if count < 2 else "max_attempts_reached"
        ),
        "original_relation_overlap": overlap,
        "original_relation_overlap_fraction": overlap / count if count else 1.0,
    }
