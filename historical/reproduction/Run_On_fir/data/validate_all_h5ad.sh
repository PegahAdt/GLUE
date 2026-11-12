#!/bin/bash
#SBATCH --job-name=glue_validate_data
#SBATCH --time=4:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/glue_validate_data_%j.out
#SBATCH --error=logs/glue_validate_data_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
mkdir -p logs

source /project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/activate_glue.sh

python - <<'PY'
from pathlib import Path
import anndata as ad

files = [
    "Chen-2019-RNA.h5ad",
    "Chen-2019-ATAC.h5ad",
    "Ma-2020-RNA.h5ad",
    "Ma-2020-ATAC.h5ad",
    "10x-Multiome-Pbmc10k-RNA.h5ad",
    "10x-Multiome-Pbmc10k-ATAC.h5ad",
    "Saunders-2018.h5ad",
    "Luo-2017.h5ad",
    "10x-ATAC-Brain5k.h5ad",
    "Cao-2020.h5ad",
    "Domcke-2020.h5ad",
    "Muto-2021-RNA.h5ad",
    "Muto-2021-ATAC.h5ad",
    "Yao-2021-RNA.h5ad",
    "Yao-2021-ATAC.h5ad",
]

base = Path("data/dataset")
missing = []
failed = []

for fname in files:
    path = base / fname
    if not path.exists() or path.stat().st_size == 0:
        print("MISSING:", path)
        missing.append(fname)
        continue

    try:
        x = ad.read_h5ad(path)
        print("PASS:", fname)
        print("  shape:", x.shape)
        print("  obs columns:", list(x.obs.columns)[:8])
        print("  var columns:", list(x.var.columns)[:8])
    except Exception as e:
        print("FAIL:", fname, type(e).__name__, e)
        failed.append(fname)

print()
print("Summary")
print("  missing:", missing)
print("  failed:", failed)

if missing or failed:
    raise SystemExit(1)
PY
