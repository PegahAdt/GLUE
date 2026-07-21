#!/bin/bash
#SBATCH --job-name=glue_dl
#SBATCH --time=24:00:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --array=0-14%2
#SBATCH --output=logs/glue_dl_%A_%a.out
#SBATCH --error=logs/glue_dl_%A_%a.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
mkdir -p logs data/dataset
cd data/dataset

BASE="ftp://ftp.cbi.pku.edu.cn/pub/GLUE/dataset"

FILES=(
  Chen-2019-RNA.h5ad
  Chen-2019-ATAC.h5ad
  Ma-2020-RNA.h5ad
  Ma-2020-ATAC.h5ad
  10x-Multiome-Pbmc10k-RNA.h5ad
  10x-Multiome-Pbmc10k-ATAC.h5ad
  Saunders-2018.h5ad
  Luo-2017.h5ad
  10x-ATAC-Brain5k.h5ad
  Cao-2020.h5ad
  Domcke-2020.h5ad
  Muto-2021-RNA.h5ad
  Muto-2021-ATAC.h5ad
  Yao-2021-RNA.h5ad
  Yao-2021-ATAC.h5ad
)

f="${FILES[$SLURM_ARRAY_TASK_ID]}"

echo "Downloading/resuming: $f"
date

wget -c \
  --timeout=120 \
  --read-timeout=120 \
  --tries=0 \
  --waitretry=30 \
  --retry-connrefused \
  "$BASE/$f"

echo "Finished: $f"
ls -lh "$f"
date
