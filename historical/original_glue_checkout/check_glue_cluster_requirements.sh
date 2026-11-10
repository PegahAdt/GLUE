#!/bin/bash
# GLUE Compute Canada cluster audit script
# Run from: /project/6001426/paa40/GLUE/GLUE
# This checks prerequisites; it does not install or modify packages.

set +e

GLUE_DIR="/project/6001426/paa40/GLUE/GLUE"
cd "$GLUE_DIR" || { echo "FAIL: Cannot cd to $GLUE_DIR"; exit 1; }

echo "=============================="
echo "GLUE CLUSTER AUDIT"
echo "Directory: $(pwd)"
echo "Date: $(date)"
echo "=============================="

pass() { echo "PASS: $1"; }
warn() { echo "WARN: $1"; }
fail() { echo "FAIL: $1"; }

echo
echo "1) Repo state"
git describe --tags --always 2>/dev/null && pass "git describe works" || fail "git describe failed"
git status --short 2>/dev/null | head -n 20
[ -d scglue ] && pass "scglue source directory exists" || fail "missing scglue directory"
[ -d data ] && pass "data directory exists" || fail "missing data directory"
[ -d evaluation ] && pass "evaluation directory exists" || warn "missing evaluation directory"
[ -d experiments ] && pass "experiments directory exists" || warn "missing experiments directory"
[ -d custom ] && pass "custom directory exists" || fail "missing custom directory"
[ -d packrat ] && pass "packrat directory exists" || warn "missing packrat directory"

echo
echo "2) Python/conda environment"
export PATH="$HOME/bin:$PATH"
export MAMBA_ROOT_PREFIX="${MAMBA_ROOT_PREFIX:-$HOME/.local/share/mamba}"
if command -v micromamba >/dev/null 2>&1; then
  pass "micromamba found: $(micromamba --version)"
  eval "$(micromamba shell hook --shell bash)"
  micromamba activate "$GLUE_DIR/conda"
else
  warn "micromamba not found in PATH"
fi

unset PYTHONPATH
export PYTHONNOUSERSITE=1

python --version
python - <<'PY'
import importlib
mods = ["scglue", "torch", "scanpy", "anndata", "numpy", "pandas", "snakemake", "jupyter"]
for m in mods:
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, "__version__", "unknown")
        path = getattr(mod, "__file__", "unknown")
        print(f"PASS: {m} {ver} :: {path}")
    except Exception as e:
        print(f"FAIL: {m} import failed: {type(e).__name__}: {e}")
PY

echo
echo "3) Command-line tools"
for exe in snakemake jupyter wget curl gzip zcat sort bedmap bedtools tabix bgzip R Rscript; do
  if command -v "$exe" >/dev/null 2>&1; then
    echo "PASS: $exe -> $(command -v "$exe")"
  else
    echo "MISSING: $exe"
  fi
done

echo
echo "4) R module / R packages"
module load r/4.3.1 >/dev/null 2>&1
export R_LIBS_USER="${R_LIBS_USER:-/project/6001426/paa40/Rlibs/glue-R-4.3-clean}"
echo "R_LIBS_USER=$R_LIBS_USER"
R --version 2>/dev/null | head -n 1 || echo "FAIL: R not available"

Rscript - <<'RSCRIPT'
.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
cat("R library paths:\n")
print(.libPaths())
pkgs <- c("SeuratObject", "Seurat", "Signac", "EnsDb.Hsapiens.v86", "dplyr", "ggplot2", "DoubletFinder")
for (pkg in pkgs) {
  ok <- requireNamespace(pkg, quietly = TRUE)
  if (ok) {
    cat("PASS:", pkg, as.character(packageVersion(pkg)), "\n")
  } else {
    cat("MISSING:", pkg, "\n")
  }
}
RSCRIPT

echo
echo "5) Genome files needed by 10x-Multiome-Pbmc10k"
GENOME_DIR="$GLUE_DIR/data/genome"
for f in \
  "$GENOME_DIR/gencode.v35.chr_patch_hapl_scaff.annotation.gtf.gz" \
  "$GENOME_DIR/gencode.v35.chr_patch_hapl_scaff.genes_with_promoters.bed" \
  "$GENOME_DIR/gencode.v35.chr_patch_hapl_scaff.genes_with_promoters.sorted.bed"; do
  [ -s "$f" ] && echo "PASS: $(ls -lh "$f")" || echo "MISSING: $f"
done

echo
echo "6) 10x-Multiome-Pbmc10k raw/intermediate files"
D="$GLUE_DIR/data/download/10x-Multiome-Pbmc10k"
for f in \
  "$D/pbmc_granulocyte_sorted_10k_filtered_feature_bc_matrix.h5" \
  "$D/pbmc_granulocyte_sorted_10k_atac_fragments.tsv.gz" \
  "$D/pbmc_granulocyte_sorted_10k_atac_fragments.tsv.gz.tbi" \
  "$D/wnn_meta_data.csv" \
  "$D/doubletfinder_inference.csv" \
  "$D/pbmc_granulocyte_sorted_10k_atac_fragments.sorted.bed" \
  "$D/pbmc_granulocyte_sorted_10k_atac_fragments.bedmap.gz"; do
  [ -s "$f" ] && echo "PASS: $(ls -lh "$f")" || echo "MISSING: $f"
done

echo
echo "7) Preprocessed paper data files, if using docs/data.rst shortcut"
for f in \
  "$GLUE_DIR/data/dataset/10x-Multiome-Pbmc10k-RNA.h5ad" \
  "$GLUE_DIR/data/dataset/10x-Multiome-Pbmc10k-ATAC.h5ad" \
  "$GLUE_DIR/data/dataset/Chen-2019-RNA.h5ad" \
  "$GLUE_DIR/data/dataset/Chen-2019-ATAC.h5ad"; do
  [ -s "$f" ] && echo "PASS: $(ls -lh "$f")" || echo "MISSING/OPTIONAL: $f"
done

echo
echo "8) Snakemake dry runs"
cd "$GLUE_DIR/data" || exit 1
snakemake -n -j1 -pr collect/10x-Multiome-Pbmc10k.html >/tmp/glue_audit_snakemake_10x.log 2>&1
if [ $? -eq 0 ]; then
  pass "data Snakemake dry-run for 10x-Multiome-Pbmc10k"
else
  warn "data Snakemake dry-run failed; see /tmp/glue_audit_snakemake_10x.log"
  tail -n 80 /tmp/glue_audit_snakemake_10x.log
fi

echo
echo "=============================="
echo "Audit complete."
echo "=============================="

