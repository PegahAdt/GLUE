#!/bin/bash
#SBATCH --job-name=glue_r_deps
#SBATCH --time=8:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --output=glue_r_deps_%j.out
#SBATCH --error=glue_r_deps_%j.err

set -eo pipefail

cd /project/6001426/paa40/GLUE/GLUE

module load r/4.3.1

export R_LIBS_USER=/project/6001426/paa40/Rlibs/glue-R-4.3
mkdir -p "$R_LIBS_USER"

echo "R version:"
R --version | head -n 1
echo "R_LIBS_USER=$R_LIBS_USER"

Rscript - <<'RSCRIPT'
.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
print(.libPaths())

options(repos = c(CRAN = "https://cloud.r-project.org"))

install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, dependencies = TRUE)
  }
}

install_if_missing("BiocManager")
install_if_missing("remotes")
install_if_missing("dplyr")
install_if_missing("ggplot2")

if (!requireNamespace("EnsDb.Hsapiens.v86", quietly = TRUE)) {
  BiocManager::install("EnsDb.Hsapiens.v86", ask = FALSE, update = FALSE)
}

if (!requireNamespace("Signac", quietly = TRUE)) {
  install.packages("Signac", dependencies = TRUE)
}

# Prefer the repo's custom Seurat tarball if present.
if (!requireNamespace("Seurat", quietly = TRUE)) {
  install.packages("custom/Seurat_4.0.2.tar.gz", repos = NULL, type = "source")
}

if (!requireNamespace("DoubletFinder", quietly = TRUE)) {
  remotes::install_github("chris-mcginnis-ucsf/DoubletFinder", upgrade = "never")
}

pkgs <- c("Seurat", "Signac", "EnsDb.Hsapiens.v86", "dplyr", "ggplot2", "DoubletFinder")
for (pkg in pkgs) {
  suppressPackageStartupMessages(library(pkg, character.only = TRUE))
  cat(pkg, as.character(packageVersion(pkg)), "\n")
}
RSCRIPT

echo "Finished installing/testing R deps."
