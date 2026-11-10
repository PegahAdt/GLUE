# Matched GAT recovery

The successful full-data task 58723587_1 used train_one.sh via train_array.sbatch, submitted by submit_all.sh from evaluation/shareseq_ma2020. Slurm accounting confirms COMPLETED in 07:59:44. Its saved run_info.yaml records GLUE_GAT/evaluation/workflow/scripts/run_GLUE.py and negative slope 0.2.

Matched task 58768924 ran from baseline GLUE root. Python -c inserts cwd before PYTHONPATH, causing the baseline package to shadow GLUE_GAT. matched_train_one.sh now changes to the validated orchestration directory; matched_train_array.sbatch also sets --chdir there. The existing architecture-specific PYTHONPATH and training entry point are retained. The import probe prints scglue.__file__ and checks exact resolved __init__.py paths. No model code, training arguments, or input manifests changed.

Only odd tasks 1,3,5,7,9,11,13,15,17 were submitted as 58973921. Metrics for the same indices are 58973943 with afterok:58973921. All nine original even GCN tasks completed; none was resubmitted. Original matched metrics 58768939 and report 58768984 were cancelled before execution. No matched GCN cell_integration.yaml exists, so the combined report awaits permission to compute those missing metrics from saved outputs.

Original report 58723589 failed because this SciPy version exposes SpearmanrResult.correlation rather than .statistic. Both accesses in postprocess.py now use .correlation. Rerun 58972736 completed successfully in 44 seconds, with 26/26 complete runs, finite metrics, and no missing runs.
