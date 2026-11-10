#!/bin/bash
set -euo pipefail
ROOT=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020
ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda
if [[ -s "$ROOT/manifests/submitted_jobs.yaml" ]]; then
  ids=$($ENV/bin/python -c 'import yaml; x=yaml.safe_load(open("'"$ROOT"'/manifests/submitted_jobs.yaml")); print(",".join(str(v) for v in x.values() if str(v).isdigit()))')
  [[ -z "$ids" ]] || squeue -j "$ids" -o '%.18i %.24j %.10T %.10M %.6D %R' || true
fi
$ENV/bin/python "$ROOT/scripts/status.py"

