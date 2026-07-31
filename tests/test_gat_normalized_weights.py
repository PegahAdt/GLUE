import torch

from scglue.models.sc import GATGraphEncoder


def make_encoder() -> GATGraphEncoder:
    encoder = GATGraphEncoder(
        vnum=3,
        out_features=1,
        negative_slope=0.2
    )

    with torch.no_grad():
        encoder.vrepr.copy_(
            torch.tensor([
                [1.0],
                [3.0],
                [0.0]
            ])
        )

        # Make h_i = r_i
        encoder.conv.weight.fill_(1.0)

        # Make learned attention scores equal for all edges.
        # Therefore, only the supplied normalized weights affect alpha.
        encoder.conv.head.zero_()

        # Make posterior mean equal to the propagated representation.
        encoder.loc.weight.fill_(1.0)
        encoder.loc.bias.zero_()

    return encoder


def test_gat_uses_normalized_weights() -> None:
    encoder = make_encoder()

    # Edges:
    # node 0 -> node 2
    # node 1 -> node 2
    eidx = torch.tensor([
        [0, 1],
        [2, 2]
    ])

    esgn = torch.tensor([
        1.0,
        1.0
    ])

    enorm = torch.tensor([
        0.8,
        0.2
    ])

    raw_weights_a = torch.tensor([
        0.5,
        0.5
    ])

    raw_weights_b = torch.tensor([
        100.0,
        1.0
    ])

    loc_a = encoder(
        eidx,
        enorm,
        esgn,
        ewt=raw_weights_a
    ).loc

    loc_b = encoder(
        eidx,
        enorm,
        esgn,
        ewt=raw_weights_b
    ).loc

    loc_without_raw = encoder(
        eidx,
        enorm,
        esgn
    ).loc

    # Changing raw ewt must have no effect.
    assert torch.allclose(loc_a, loc_b, atol=1e-6)
    assert torch.allclose(
        loc_a,
        loc_without_raw,
        atol=1e-6
    )

    # At target node 2:
    #
    # 0.8 * 1.0 + 0.2 * 3.0 = 1.4
    assert torch.allclose(
        loc_a[2],
        torch.tensor([1.4]),
        atol=1e-6
    )

    reversed_enorm = torch.tensor([
        0.2,
        0.8
    ])

    loc_reversed = encoder(
        eidx,
        reversed_enorm,
        esgn,
        ewt=raw_weights_a
    ).loc

    # Changing enorm must change the result:
    #
    # 0.2 * 1.0 + 0.8 * 3.0 = 2.6
    assert torch.allclose(
        loc_reversed[2],
        torch.tensor([2.6]),
        atol=1e-6
    )

    assert not torch.allclose(
        loc_a,
        loc_reversed
    )


if __name__ == "__main__":
    test_gat_uses_normalized_weights()
    print("Normalized-weight GAT test passed.")
