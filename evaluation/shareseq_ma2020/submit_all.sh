#!/bin/bash
set -euo pipefail
ROOT=/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020
ENV=/project/6001426/paa40/GlUE_Exp/GLUE/conda
export PATH="$ENV/bin:$PATH"
cd "$ROOT"
if [[ -s manifests/master_experiment_manifest.csv && -s analysis/dataset_inventory.yaml && -s data/guidance.graphml.gz && -s data/rna_prepared.h5ad && -s data/atac_prepared.h5ad ]]; then
  echo "Reusing validated preparation artifacts"
else
  "$ENV/bin/python" scripts/prepare.py | tee analysis/preparation_summary.txt
fi
if [[ ! -s results/smoke_gated_500/SMOKE_OK ]]; then
  if [[ -s results/smoke_gated_500/final.dill ]]; then
    smoke_job=$(sbatch --parsable slurm/rescue_smoke.sbatch)
  else
    smoke_job=$(sbatch --parsable slurm/smoke.sbatch)
  fi
  echo "Smoke submitted: $smoke_job. Rerun submit_all.sh after it succeeds."
  exit 0
fi
smoke_job=$(awk '/Validated by job/ {print $4}' results/smoke_gated_500/SMOKE_OK)
[[ "$smoke_job" =~ ^[0-9]+$ ]] || { echo "Missing validated smoke job ID" >&2; exit 1; }
state=$(sacct -X -j "$smoke_job" --format=State -n -P | head -1)
[[ "$state" == COMPLETED ]] || { echo "Smoke $smoke_job is $state; training not submitted" >&2; exit 1; }
# Accounting above confirms smoke success; completed jobs may already be purged
# from the controller and cannot reliably be used in a new afterok dependency.
train_job=$(sbatch --parsable slurm/train_array.sbatch)
metrics_job=$(sbatch --parsable --dependency=afterok:"$train_job" slurm/evaluate_array.sbatch)
report_job=$(sbatch --parsable --dependency=afterok:"$metrics_job" slurm/postprocess.sbatch)
"$ENV/bin/python" scripts/record_jobs.py "$smoke_job" "$train_job" "$metrics_job" "$report_job"
printf 'smoke=%s\ntraining=%s\nmetrics_and_gates=%s\nanalysis_and_report=%s\n' "${smoke_job:-reused}" "$train_job" "$metrics_job" "$report_job"
