r"""
Neural network modules, datasets & data loaders, and other utilities
"""

import functools
import os
from math import sqrt

import numpy as np
import pynvml
import torch
import torch.nn.functional as F
from torch.nn.modules.batchnorm import _NormBase

from ..utils import config, logged


#-------------------------- Neural network modules -----------------------------

class GraphConv(torch.nn.Module):

    r"""
    Graph convolution (propagation only)
    """

    def forward(
            self, input: torch.Tensor, eidx: torch.Tensor,
            enorm: torch.Tensor, esgn: torch.Tensor
    ) -> torch.Tensor:
        r"""
        Forward propagation

        Parameters
        ----------
        input
            Input data (:math:`n_{vertices} \times n_{features}`)
        eidx
            Vertex indices of edges (:math:`2 \times n_{edges}`)
        enorm
            Normalized weight of edges (:math:`n_{edges}`)
        esgn
            Sign of edges (:math:`n_{edges}`)

        Returns
        -------
        result
            Graph convolution result (:math:`n_{vertices} \times n_{features}`)
        """
        sidx, tidx = eidx  # source index and target index
        message = input[sidx] * (esgn * enorm).unsqueeze(1)  # n_edges * n_features
        res = torch.zeros_like(input)
        tidx = tidx.unsqueeze(1).expand_as(message)  # n_edges * n_features
        res.scatter_add_(0, tidx, message)
        return res


class GraphAttent(torch.nn.Module):  # pragma: no cover

    r"""
    Graph attention

    Parameters
    ----------
    in_features
        Input dimensionality
    out_featres
        Output dimensionality

    Note
    ----
    **EXPERIMENTAL**
    """

    def __init__(self, in_features: int, out_features: int) -> None:
        super().__init__()
        self.weight = torch.nn.ParameterDict({
            "pos": torch.nn.Parameter(torch.Tensor(out_features, in_features)),
            "neg": torch.nn.Parameter(torch.Tensor(out_features, in_features))
        })
        self.head = torch.nn.ParameterDict({
            "pos": torch.nn.Parameter(torch.zeros(out_features * 2)),
            "neg": torch.nn.Parameter(torch.zeros(out_features * 2))
        })
        torch.nn.init.kaiming_uniform_(self.weight["pos"], sqrt(5))  # Following torch.nn.Linear
        torch.nn.init.kaiming_uniform_(self.weight["neg"], sqrt(5))  # Following torch.nn.Linear

    def forward(
            self, input: torch.Tensor, eidx: torch.Tensor,
            ewt: torch.Tensor, esgn: torch.Tensor
    ) -> torch.Tensor:
        r"""
        Forward propagation

        Parameters
        ----------
        input
            Input data (:math:`n_{vertices} \times n_{features}`)
        eidx
            Vertex indices of edges (:math:`2 \times n_{edges}`)
        ewt
            Weight of edges (:math:`n_{edges}`)
        esgn
            Sign of edges (:math:`n_{edges}`)

        Returns
        -------
        result
            Graph attention result (:math:`n_{vertices} \times n_{features}`)
        """
        res_dict = {}
        for sgn in ("pos", "neg"):
            mask = esgn == 1 if sgn == "pos" else esgn == -1
            sidx, tidx = eidx[:, mask]
            ptr = input @ self.weight[sgn].T
            alpha = torch.cat([ptr[sidx], ptr[tidx]], dim=1) @ self.head[sgn]
            alpha = F.leaky_relu(alpha, negative_slope=0.2).exp() * ewt[mask]
            normalizer = torch.zeros(ptr.shape[0], device=ptr.device)
            normalizer.scatter_add_(0, tidx, alpha)
            alpha = alpha / normalizer[tidx]  # Only entries with non-zero denominators will be used
            message = ptr[sidx] * alpha.unsqueeze(1)
            res = torch.zeros_like(ptr)
            tidx = tidx.unsqueeze(1).expand_as(message)
            res.scatter_add_(0, tidx, message)
            res_dict[sgn] = res
        return res_dict["pos"] + res_dict["neg"]




def _incoming_edge_softmax(
        logits: torch.Tensor,
        tidx: torch.Tensor
) -> torch.Tensor:
    r"""
    Apply softmax separately to the incoming edges of each target node.

    Parameters
    ----------
    logits
        One attention logit per edge
    tidx
        Target-node index of each edge

    Returns
    -------
    alpha
        One normalized attention coefficient per edge
    """

    if logits.numel() == 0:
        return logits

    # Put edges with the same target next to one another
    order = torch.argsort(tidx)

    sorted_tidx = tidx[order]
    sorted_logits = logits[order]

    # Count how many incoming edges each represented target has
    _, counts = torch.unique_consecutive(
        sorted_tidx,
        return_counts=True
    )

    # Split the logits into one tensor per target node
    logit_groups = torch.split(
        sorted_logits,
        counts.detach().cpu().tolist()
    )

    # Apply an independent softmax to each target's incoming edges
    sorted_alpha = torch.cat(
        [
            torch.softmax(group, dim=0)
            for group in logit_groups
        ],
        dim=0
    )

    # Restore the original edge order
    inverse_order = torch.argsort(order)

    return sorted_alpha[inverse_order]


class SignedPriorGraphAttention(torch.nn.Module):
    r"""
    Single-head signed, prior-weighted graph attention.

    For each directed edge j -> i:

        h_i = W r_i

        e_ji = LeakyReLU(
            a^T [h_i || h_j]
        )

        alpha_ji = softmax over incoming edges of
                   (e_ji + log w_ji)

        p_i = sum_j s_ji alpha_ji h_j

    Parameters
    ----------
    in_features
        Input node-vector dimensionality
    out_features
        Transformed node-vector dimensionality
    negative_slope
        Negative slope used by LeakyReLU
    """

    def __init__(
            self,
            in_features: int,
            out_features: int,
            negative_slope: float = 0.2
    ) -> None:
        super().__init__()

        self.in_features = in_features
        self.out_features = out_features
        self.negative_slope = negative_slope

        # W from the GAT equations
        self.weight = torch.nn.Parameter(
            torch.Tensor(
                out_features,
                in_features
            )
        )

        # a from the GAT equations
        self.head = torch.nn.Parameter(
            torch.zeros(
                2 * out_features
            )
        )

        # Initialize W using the same general style as torch Linear layers
        torch.nn.init.kaiming_uniform_(
            self.weight,
            sqrt(5)
        )

    def forward(
            self,
            input: torch.Tensor,
            eidx: torch.Tensor,
            ewt: torch.Tensor,
            esgn: torch.Tensor
    ) -> torch.Tensor:
        r"""
        Perform signed, prior-weighted attention propagation.

        Parameters
        ----------
        input
            Trainable node representations
            with shape (n_vertices, in_features)
        eidx
            Edge source and target indices
            with shape (2, n_edges)
        ewt
            Positive edge weights supplied as the attention prior
            with shape (n_edges,)
        esgn
            Fixed edge signs, either +1 or -1,
            with shape (n_edges,)

        Returns
        -------
        result
            Propagated node representations
            with shape (n_vertices, out_features)
        """

        # Check the edge-index shape
        if eidx.ndim != 2 or eidx.shape[0] != 2:
            raise ValueError(
                "`eidx` must have shape (2, n_edges)!"
            )

        # Check that weights and signs are vectors
        if ewt.ndim != 1:
            raise ValueError(
                "`ewt` must be one-dimensional!"
            )

        if esgn.ndim != 1:
            raise ValueError(
                "`esgn` must be one-dimensional!"
            )

        # Check that all edge arrays describe the same number of edges
        if (
                eidx.shape[1] != ewt.numel()
                or ewt.numel() != esgn.numel()
        ):
            raise ValueError(
                "Edge indices, weights and signs "
                "must contain the same number of edges!"
            )

        # If the graph has no edges, return zero vectors
        if ewt.numel() == 0:
            return torch.zeros(
                input.shape[0],
                self.out_features,
                dtype=input.dtype,
                device=input.device
            )

        # The attention equation contains log(w_ji),
        # so every supplied edge weight must be positive
        if torch.any(ewt <= 0).item():
            raise ValueError(
                "GAT attention-prior edge weights must be positive!"
            )

        # GLUE signs must be +1 or -1
        valid_signs = torch.logical_or(
            esgn == 1,
            esgn == -1
        )

        if not torch.all(valid_signs).item():
            raise ValueError(
                "GAT edge signs must be either +1 or -1!"
            )

        # For an edge j -> i:
        # sidx contains source node j
        # tidx contains target node i
        sidx, tidx = eidx

        # h_i = W r_i
        #
        # input shape:
        #     (n_vertices, in_features)
        #
        # self.weight.T shape:
        #     (in_features, out_features)
        #
        # h shape:
        #     (n_vertices, out_features)
        h = input @ self.weight.T

        # Match fixed edge values to h's floating-point type
        ewt = ewt.to(dtype=h.dtype)
        esgn = esgn.to(dtype=h.dtype)

        # For every edge j -> i, construct:
        #
        # [h_i || h_j]
        #
        # target first, source second
        endpoint_repr = torch.cat(
            [
                h[tidx],
                h[sidx]
            ],
            dim=1
        )

        # a^T [h_i || h_j]
        score = endpoint_repr @ self.head

        # e_ji = LeakyReLU(a^T [h_i || h_j])
        score = F.leaky_relu(
            score,
            negative_slope=self.negative_slope
        )

        # Add the fixed prior-weight bias:
        #
        # e_ji + log(w_ji)
        attention_logits = (
            score
            + torch.log(ewt)
        )

        # Normalize separately over all incoming edges
        # of each target node
        alpha = _incoming_edge_softmax(
            attention_logits,
            tidx
        )

        # Signed message:
        #
        # m_{j -> i} =
        #     s_ji * alpha_ji * h_j
        message = h[sidx] * (
            esgn * alpha
        ).unsqueeze(1)

        # Prepare one output vector for every graph node
        result = torch.zeros_like(h)

        # Repeat each target index across all vector coordinates
        expanded_tidx = tidx.unsqueeze(1).expand_as(
            message
        )

        # Add all incoming messages to their target nodes
        result.scatter_add_(
            0,
            expanded_tidx,
            message
        )

        return result










#----------------------------- Utility functions -------------------------------

def freeze_running_stats(m: torch.nn.Module) -> None:
    r"""
    Selectively stops normalization layers from updating running stats

    Parameters
    ----------
    m
        Network module
    """
    if isinstance(m, _NormBase):
        m.eval()


def get_default_numpy_dtype() -> type:
    r"""
    Get numpy dtype matching that of the pytorch default dtype

    Returns
    -------
    dtype
        Default numpy dtype
    """
    return getattr(np, str(torch.get_default_dtype()).replace("torch.", ""))


@logged
@functools.lru_cache(maxsize=1)
def autodevice() -> torch.device:
    r"""
    Get torch computation device automatically
    based on GPU availability and memory usage

    Returns
    -------
    device
        Computation device
    """
    used_device = -1
    if not config.CPU_ONLY:
        try:
            pynvml.nvmlInit()
            free_mems = np.array([
                pynvml.nvmlDeviceGetMemoryInfo(
                    pynvml.nvmlDeviceGetHandleByIndex(i)
                ).free for i in range(pynvml.nvmlDeviceGetCount())
            ])
            for item in config.MASKED_GPUS:
                free_mems[item] = -1
            best_devices = np.where(free_mems == free_mems.max())[0]
            used_device = np.random.choice(best_devices, 1)[0]
            if free_mems[used_device] < 0:
                used_device = -1
        except pynvml.NVMLError:
            pass
    if used_device == -1:
        autodevice.logger.info("Using CPU as computation device.")
        return torch.device("cpu")
    autodevice.logger.info("Using GPU %d as computation device.", used_device)
    os.environ["CUDA_VISIBLE_DEVICES"] = str(used_device)
    return torch.device("cuda")
