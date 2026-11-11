# PBMC learned edge analysis

Canonical configuration and submission: `CLEANUP_EXPERIMENT_ORCHESTRATION:experiments/pbmc/learned_edge_analysis`.

This architecture checkout supplies the implementation below; it does not maintain a second dispatcher.

Training: `reuse ten GATED models`

Evaluation: `evaluation/extract_gated_edge_analysis.py; evaluation/gate_analysis/build_gated_edge_analysis_report.py`

The report generator was incorrectly ignored before preservation. It remains tracked; learned gate tables and PDF/HTML output remain external.

Status: Ten reused models analyzed; generated reports excluded
