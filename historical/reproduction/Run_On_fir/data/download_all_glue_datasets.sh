#!/bin/bash
#SBATCH --job-name=glue_all_data
#SBATCH --time=12:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2
#SBATCH --output=logs/glue_all_data_%j.out
#SBATCH --error=logs/glue_all_data_%j.err

set -eo pipefail

cd /home/chauvec/project/paa40/GlUE_Exp/GLUE

mkdir -p logs
mkdir -p data/dataset
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

for f in "${FILES[@]}"; do
  echo "Downloading $f"
  wget -c --timeout=60 --tries=20 --waitretry=10 "$BASE/$f"
done

echo "Downloaded files:"
ls -lh *.h5ad
