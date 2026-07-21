#!/bin/bash
#SBATCH --job-name=glue_packrat
#SBATCH --time=24:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/glue_packrat_%j.out
#SBATCH --error=logs/glue_packrat_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
mkdir -p logs

module load r/4.3.1

R --version
Rscript --version

export R_LIBS_USER=/project/6001426/paa40/GlUE_Exp/GLUE/r-lib/R-4.3.1
mkdir -p "$R_LIBS_USER"

unset CONDA_PREFIX || true
unset CONDA_DEFAULT_ENV || true
unset MAMBA_ROOT_PREFIX || true
unset PYTHONPATH || true
unset PYTHONNOUSERSITE || true
unset LD_LIBRARY_PATH || true
unset LIBRARY_PATH || true
unset CPATH || true
unset C_INCLUDE_PATH || true
unset CPLUS_INCLUDE_PATH || true
unset PKG_CONFIG_PATH || true

Rscript - <<'RSCRIPT'
local_lib <- Sys.getenv("R_LIBS_USER")
dir.create(local_lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(local_lib, .libPaths()))

repos <- c(
    CRAN = "https://cloud.r-project.org",
    BioCsoft = "https://bioconductor.org/packages/3.12/bioc",
    BioCann = "https://bioconductor.org/packages/3.12/data/annotation",
    BioCexp = "https://bioconductor.org/packages/3.12/data/experiment",
    BioCworkflows = "https://bioconductor.org/packages/3.12/workflows"
)

options(repos = repos)

cat("R library paths:\n")
print(.libPaths())

cat("Repositories:\n")
print(getOption("repos"))

if (!requireNamespace("packrat", quietly = TRUE)) {
    install.packages("packrat", lib = local_lib)
}

library(packrat)

packrat::restore(restart = FALSE)

if (file.exists("data/download/Saunders-2018/DropSeq.util_2.0.tar.gz")) {
    install.packages(
        "data/download/Saunders-2018/DropSeq.util_2.0.tar.gz",
        repos = NULL
    )
} else {
    message("DropSeq.util tarball not found yet. This matters only for relevant raw preprocessing rules.")
}

if (file.exists("custom/Seurat_4.0.2.tar.gz")) {
    dir.create("packrat/custom", recursive = TRUE, showWarnings = FALSE)
    install.packages(
        "custom/Seurat_4.0.2.tar.gz",
        lib = "packrat/custom",
        repos = NULL
    )
} else {
    message("custom/Seurat_4.0.2.tar.gz not found.")
}
RSCRIPT
