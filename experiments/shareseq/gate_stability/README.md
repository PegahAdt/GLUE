# SHARE-seq GATED gate stability

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/shareseq/gate_stability`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `evaluation/shareseq_gate_stability/experiment.py run A|B TASK`

Evaluation: `evaluation/shareseq_gate_stability/analyze.py`

A:12 dimensions16–1024 x gates .25,.50,.75,.95 x seeds0–2=144. B:1536,2048,3072,4096 x same gates/seeds=48. Manifest row task_id is contiguous within A or B. Resources A4CPU/32G/3h30; B4CPU/48G/4h template, historically overridden to12h or18h. Retain exact original manifests/edge IDs/preflight. Analysis thresholds .25,.50,.75; all192 completion markers required. This catalog entry intentionally cannot submit into active paths.

Status: A:109/144 finalized +35 pending; B:29/48 finalized +19 pending (one already trained); final analysis pending
