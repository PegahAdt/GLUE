#!/bin/bash
set -euo pipefail
source /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/environment.sh
MODE=${1:-help}
[[ $# -eq 0 ]] || shift
case "$MODE" in
    prepare)
        export CUDA_VISIBLE_DEVICES=""
        exec "$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/prepare.py" --verify-gated-models "$@"
        ;;
    test)
        export CUDA_VISIBLE_DEVICES="" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
        "$GCN_ENV/bin/python" -B -m pytest --noconftest tests/test_pbmc_gcn_subsampling.py tests/test_pbmc_evaluation.py -q
        "$GCN_ENV/bin/python" -B -c 'import sys; sys.path.insert(0,"evaluation/pbmc_graph_subsampling_gcn/scripts"); from common import save_json,EXPERIMENT,sha; save_json(EXPERIMENT/"validation/tests.json",{"status":"passed","test_files":["tests/test_pbmc_gcn_subsampling.py","tests/test_pbmc_evaluation.py"],"source_hashes":{p:sha(p) for p in ["tests/test_pbmc_gcn_subsampling.py","tests/test_pbmc_evaluation.py"]}})'
        ;;
    submit)
        exec "$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/submit_pipeline.py" "$@"
        ;;
    preflight|report)
        export CUDA_VISIBLE_DEVICES=""
        exec "$GCN_ENV/bin/python" -B -u "$GCN_EXPERIMENT/scripts/evaluate.py" --mode "$MODE" "$@"
        ;;
    *)
        echo 'Usage: bash evaluation/pbmc_graph_subsampling_gcn/run.sh {prepare|test|submit|preflight|report} [options]'
        exit 2
        ;;
esac
