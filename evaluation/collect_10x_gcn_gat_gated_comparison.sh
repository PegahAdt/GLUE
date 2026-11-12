#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python collect_10x_gcn_gat_gated_comparison.py
