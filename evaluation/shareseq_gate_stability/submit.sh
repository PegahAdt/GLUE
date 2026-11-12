#!/bin/bash
set -euo pipefail
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/environment.sh
python -u experiment.py prepare
python -u experiment.py preflight
exec python -u experiment.py submit
