r"""Tests for static edge-gated graph encoding."""

import math
import importlib.util
import pathlib
import sys

import pytest
import torch

import scglue
from scglue.models.nn import EdgeGatedGraphConv, GraphConv
from scglue.models.sc import GatedGraphEncoder

from ..fixtures import *  # pylint: disable=wildcard-import,unused-wildcard-import


def test_edge_gated_graph_conv_signed_sum_and_fixed_denominator():
    conv = EdgeGatedGraphConv()
    inputs = torch.tensor([[2.0], [3.0], [0.0]])
    eidx = torch.tensor([[0, 1], [2, 2]])
    enorm = torch.tensor([0.25, 0.5])
    esgn = torch.tensor([1.0, -1.0])

    result = conv(inputs, eidx, enorm, esgn, torch.tensor([0.5, 0.8]))
    assert torch.allclose(result[2], torch.tensor([-0.95]))

    attenuated = conv(inputs, eidx, enorm, esgn, torch.tensor([0.1, 0.8]))
    assert torch.allclose(attenuated[2], torch.tensor([-1.15]))
    # The second contribution remains -3 * 0.5 * 0.8 = -1.2.
    assert torch.allclose(
        attenuated[2] - 2.0 * 0.25 * 0.1, torch.tensor([-1.2])
    )


@pytest.mark.parametrize("gate_init", [0, 1, -0.1, 1.1, float("nan"), float("inf")])
def test_invalid_gate_init(gate_init):
    with pytest.raises(ValueError):
        GatedGraphEncoder(3, 2, gate_init=gate_init)


def test_gate_initialization_self_loop_and_accessors():
    encoder = GatedGraphEncoder(3, 2, gate_init=0.95)
    eidx = torch.tensor([[0, 0, 1], [0, 1, 2]])
    encoder.configure_edges(eidx)

    assert encoder.gate_logits.shape == (2,)
    assert torch.allclose(
        encoder.gate_logits,
        torch.full((2,), math.log(0.95 / 0.05)), atol=1e-6
    )
    assert torch.allclose(encoder.activated_gates(), torch.tensor([1.0, 0.95, 0.95]))
    info = encoder.get_gate_info()
    assert info["is_self_loop"].tolist() == [True, False, False]
    assert math.isnan(info["logit"][0])
    info["gate"].zero_()
    assert torch.allclose(encoder.activated_gates(), torch.tensor([1.0, 0.95, 0.95]))


def test_zero_logit_gradient_optimizer_and_keep_loss():
    encoder = GatedGraphEncoder(2, 1, gate_init=0.5)
    eidx = torch.tensor([[0], [1]])
    encoder.configure_edges(eidx)
    with torch.no_grad():
        encoder.vrepr.copy_(torch.tensor([[2.0], [0.0]]))
    assert torch.allclose(encoder.activated_gates(), torch.tensor([0.5]))
    assert torch.allclose(encoder.gate_keep_loss(), torch.tensor(0.25))

    optimizer = torch.optim.SGD(encoder.parameters(), lr=0.1)
    before = encoder.gate_logits.detach().clone()
    loss = encoder(
        eidx, torch.ones(1), torch.ones(1)
    ).mean[1].square() + encoder.gate_keep_loss()
    loss.backward()
    assert torch.isfinite(encoder.gate_logits.grad).all()
    assert encoder.gate_logits.grad.abs().sum() > 0
    optimizer.step()
    assert not torch.equal(before, encoder.gate_logits)


def test_encoder_distribution_and_topology_validation():
    encoder = GatedGraphEncoder(3, 2)
    eidx = torch.tensor([[0, 1, 2], [1, 2, 2]])
    encoder.configure_edges(eidx)
    distribution = encoder(eidx, torch.ones(3), torch.tensor([1.0, -1.0, 1.0]))
    assert distribution.mean.shape == (3, 2)
    assert torch.isfinite(distribution.stddev).all()
    assert (distribution.stddev > 0).all()
    reordered = eidx.flip(1)
    encoder.configure_edges(reordered)
    reordered_distribution = encoder(
        reordered, torch.ones(3), torch.tensor([1.0, -1.0, 1.0]).flip(0)
    )
    assert torch.allclose(distribution.mean, reordered_distribution.mean)
    different = torch.tensor([[0, 1, 2], [2, 2, 2]])
    with pytest.raises(RuntimeError, match="topology"):
        encoder.configure_edges(different)
    with pytest.raises(ValueError, match="topology"):
        encoder(different, torch.ones(3), torch.ones(3))
    with pytest.raises(ValueError, match="Duplicate"):
        GatedGraphEncoder(2, 1).configure_edges(torch.tensor([[0, 0], [1, 1]]))


def test_state_dict_round_trip_and_gcn_unchanged():
    eidx = torch.tensor([[0, 1], [1, 2]])
    source = GatedGraphEncoder(3, 2)
    target = GatedGraphEncoder(3, 2)
    source.configure_edges(eidx)
    target.configure_edges(eidx)
    with torch.no_grad():
        source.gate_logits.copy_(torch.tensor([-1.0, 2.0]))
    target.load_state_dict(source.state_dict())
    assert torch.equal(target.configured_eidx, eidx)
    assert torch.allclose(target.activated_gates(), source.activated_gates())

    inputs = torch.randn(3, 2)
    enorm = torch.tensor([0.2, 0.7])
    esgn = torch.tensor([1.0, -1.0])
    expected = GraphConv()(inputs, eidx, enorm, esgn)
    assert torch.equal(GraphConv()(inputs, eidx, enorm, esgn), expected)


def _make_model(rna_pp, atac_pp, prior, architecture):
    scglue.models.configure_dataset(
        rna_pp, "NB", use_rep="X_pca", use_highly_variable=True
    )
    scglue.models.configure_dataset(
        atac_pp, "NB", use_rep="X_lsi", use_highly_variable=True
    )
    return scglue.models.SCGLUEModel(
        {"rna": rna_pp, "atac": atac_pp}, sorted(prior.nodes),
        latent_dim=2, graph_encoder=architecture
    )


def test_model_selection_lifecycle_optimizer_adoption_and_save(
        rna_pp, atac_pp, prior, tmp_path
):
    gcn = _make_model(rna_pp, atac_pp, prior, "gcn")
    assert type(gcn.net.g2v).__name__ == "GraphEncoder"
    with pytest.raises(ValueError, match="Unknown graph encoder"):
        _make_model(rna_pp, atac_pp, prior, "unknown")

    source = _make_model(rna_pp, atac_pp, prior, "gated")
    with pytest.raises(RuntimeError, match="configure_graph_encoder"):
        source.compile()
    source.configure_graph_encoder(prior)
    source.compile(lam_keep=0.5)
    optimizer_params = {
        id(parameter)
        for group in source.trainer.vae_optim.param_groups
        for parameter in group["params"]
    }
    assert id(source.net.g2v.gate_logits) in optimizer_params

    target = _make_model(rna_pp, atac_pp, prior, "gated")
    target.configure_graph_encoder(prior)
    with torch.no_grad():
        source.net.g2v.gate_logits.add_(1)
    target.adopt_pretrained_model(source)
    assert torch.equal(target.net.g2v.gate_logits, source.net.g2v.gate_logits)

    reordered_prior = type(prior)()
    reordered_prior.add_nodes_from(prior.nodes(data=True))
    reordered_prior.add_edges_from(reversed(list(prior.edges(data=True))))
    reordered = _make_model(rna_pp, atac_pp, prior, "gated")
    reordered.configure_graph_encoder(reordered_prior)
    reordered.adopt_pretrained_model(source)
    source_info = source.get_graph_gates()
    reordered_info = reordered.get_graph_gates()
    source_gates = {
        (int(i), int(j)): float(g) for i, j, g in zip(
            source_info["source"], source_info["target"], source_info["gate"]
        )
    }
    assert all(
        float(g) == pytest.approx(source_gates[(int(i), int(j))])
        for i, j, g in zip(
            reordered_info["source"], reordered_info["target"],
            reordered_info["gate"]
        )
    )

    source.save(tmp_path / "gated.dill")
    restored = scglue.models.load_model(tmp_path / "gated.dill")
    assert restored.graph_encoder == "gated"
    assert torch.equal(
        restored.net.g2v.configured_eidx, source.net.g2v.configured_eidx
    )
    assert torch.allclose(
        restored.net.g2v.activated_gates(), source.net.g2v.activated_gates()
    )

    different_prior = prior.copy()
    different_prior.remove_edge(*next(iter(different_prior.edges)))
    incompatible = _make_model(rna_pp, atac_pp, prior, "gated")
    incompatible.configure_graph_encoder(different_prior)
    with pytest.raises(ValueError, match="topology mismatch"):
        incompatible.adopt_pretrained_model(source)
    with pytest.raises(ValueError, match="different graph encoder"):
        gcn.adopt_pretrained_model(source)
    with pytest.raises(ValueError, match="different graph encoder"):
        source.adopt_pretrained_model(gcn)


def test_evaluation_cli_gated_options(monkeypatch):
    script = pathlib.Path(__file__).parents[2] / "evaluation/workflow/scripts/run_GLUE.py"
    spec = importlib.util.spec_from_file_location("run_GLUE_gated_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = [
        "run_GLUE.py", "--input-rna", "rna.h5ad", "--input-atac", "atac.h5ad",
        "--prior", "prior.graphml", "--train-dir", "train",
        "--output-rna", "rna.csv", "--output-atac", "atac.csv",
        "--output-feature", "feature.csv", "--run-info", "run.yaml"
    ]
    monkeypatch.setattr(sys, "argv", required)
    defaults = module.parse_args()
    assert defaults.graph_encoder == "gcn"
    assert defaults.gate_init == 0.95
    assert defaults.lam_keep == 0.0

    monkeypatch.setattr(sys, "argv", required + [
        "--graph-encoder", "gated", "--gate-init", "0.8", "--lam-keep", "0.3"
    ])
    gated = module.parse_args()
    assert (gated.graph_encoder, gated.gate_init, gated.lam_keep) == (
        "gated", 0.8, 0.3
    )
    with pytest.raises(SystemExit):
        monkeypatch.setattr(sys, "argv", required + ["--gate-init", "nan"])
        module.parse_args()
