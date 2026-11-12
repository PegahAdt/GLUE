#!/bin/bash
set -euo pipefail
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/environment.sh
exec python -u analyze.py "$@"
