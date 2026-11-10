#!/bin/bash
#SBATCH --job-name=glue_r_clean
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4
#SBATCH --output=glue_r_clean_%j.out
#SBATCH --error=glue_r_clean_%j.err

set -eo pipefail

cd /project/6001426/paa40/GLUE/GLUE

# Clean module/R environment. Do NOT activate GLUE conda here.
module --force purge || true
module load StdEnv/2023
module load gcc/12.3
module load r/4.3.1

# Remove inherited conda/micromamba build paths.
unset CONDA_PREFIX || true
unset CONDA_DEFAULT_ENV || true
unset MAMBA_ROOT_PREFIX || true
unset PYTHONPATH || true
unset LD_LIBRARY_PATH || true
unset LIBRARY_PATH || true
unset CPATH || true
unset C_INCLUDE_PATH || true
unset CPLUS_INCLUDE_PATH || true
unset PKG_CONFIG_PATH || true

# Remove GLUE conda bin from PATH if inherited by sbatch.
export PATH=$(echo "$PATH" | tr ':' '\n' | grep -v '/GLUE/GLUE/conda' | paste -sd:)

export R_LIBS_USER=/project/6001426/paa40/Rlibs/glue-R-4.3-clean
mkdir -p "$R_LIBS_USER"

echo "R:"
R --version | head -n 1
echo "gcc:"
gcc --version | head -n 1
echo "R_LIBS_USER=$R_LIBS_USER"
echo "PATH=$PATH"

Rscript - <<'RSCRIPT'
.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
print(.libPaths())

options(repos = c(CRAN = "https://cloud.r-project.org"))
options(Ncpus = 4)

install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, dependencies = TRUE)
  }
}

install_if_missing("remotes")
install_if_missing("BiocManager")
install_if_missing("dplyr")
install_if_missing("ggplot2")

# Seurat 4.x-compatible SeuratObject.
if (!requireNamespace("SeuratObject", quietly = TRUE)) {
  remotes::install_version(
    "SeuratObject",
    version = "4.1.3",
    repos = "https://cloud.r-project.org",
    upgrade = "never"
  )
}

# Repo-pinned Seurat.
install.packages("custom/Seurat_4.0.2.tar.gz", repos = NULL, type = "source")

# Signac for WNN preprocessing.
if (!requireNamespace("Signac", quietly = TRUE)) {
  remotes::install_version(
    "Signac",
    version = "1.7.0",
    repos = "https://cloud.r-project.org",
    upgrade = "never"
  )
}

# Bioconductor annotation package.
if (!requireNamespace("EnsDb.Hsapiens.v86", quietly = TRUE)) {
  BiocManager::install("EnsDb.Hsapiens.v86", ask = FALSE, update = FALSE)
}

# DoubletFinder.
if (!requireNamespace("DoubletFinder", quietly = TRUE)) {
  remotes::install_github("chris-mcginnis-ucsf/DoubletFinder", upgrade = "never")
}

pkgs <- c(
  "SeuratObject",
  "Seurat",
  "Signac",
  "EnsDb.Hsapiens.v86",
  "dplyr",
  "ggplot2",
  "DoubletFinder"
)

for (pkg in pkgs) {
  suppressPackageStartupMessages(library(pkg, character.only = TRUE))
  cat(pkg, as.character(packageVersion(pkg)), "\n")
}
RSCRIPT

echo "Finished clean R dependency installation."
