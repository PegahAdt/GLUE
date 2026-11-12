# Isolated scientific source versions

Use an explicit implementation root in an external workspace; do not combine different `scglue` packages in one process. Snapshots are immutable scientific versions. Shared utilities and configurations are at the repository root.

| Role | Root | Source commit | Scope |
|---|---|---|---|
| gat | `implementations/gat` | 71e15179a48adc295bf9068d6d483ff928a2db76 | preserved, not refactored |
| gat_normalized | `implementations/gat_normalized` | 5ac0b073a5f0a372a472605d8fc61a39def55b31 | preserved, not refactored |
| gated | `implementations/gated` | 2935b8319ff6d838af7f7282255a7748d1c6afe9 | preserved, not refactored |
| gated_pbmc | `implementations/gated_pbmc` | ed1786f3429bb0f5591be628fd405f2fa90bf08e | PBMC runner kept distinct; model is byte-identical to GATED |
| gcn | `.` | 38726c508909e62a83326d2a7fed93dce438c8cb | original baseline package and runner unchanged |

[Architecture explanation](../ARCHITECTURE.md) · [Full package/runner hashes](../provenance/implementation_versions.json).

The `gated_pbmc/scglue` symlink deliberately shares the byte-identical GATED model, while its runner preserves the PBMC graph perturbation CLI and zero-edge diagnostics. Linux symlink behavior is checked; Windows checkout behavior is not verified. The normalized GAT option has no approved local thesis design.
