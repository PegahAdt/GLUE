#!/bin/bash
#SBATCH --job-name=preprocess_10x_multiome
#SBATCH --time=6:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=preprocess_10x_multiome_%j.out
#SBATCH --error=preprocess_10x_multiome_%j.err

set -eo pipefail

cd /project/6001426/paa40/GLUE/GLUE/data/download/10x-Multiome-Pbmc10k

export PATH="$HOME/bin:$PATH"
export MAMBA_ROOT_PREFIX="$HOME/.local/share/mamba"
eval "$(micromamba shell hook --shell bash)"
micromamba activate /project/6001426/paa40/GLUE/GLUE/conda

unset PYTHONPATH
export PYTHONNOUSERSITE=1

echo "Node: $(hostname)"
echo "Started: $(date)"
echo "Python:"
python --version

echo "R:"
module load r/4.3.1
export R_LIBS_USER=/project/6001426/paa40/Rlibs/glue-R-4.3
R --version | head -n 1 || true
echo "bedmap:"
bedmap --version || true

echo "Checking required inputs..."
ls -lh pbmc_granulocyte_sorted_10k_filtered_feature_bc_matrix.h5
ls -lh pbmc_granulocyte_sorted_10k_atac_fragments.tsv.gz
ls -lh pbmc_granulocyte_sorted_10k_atac_fragments.tsv.gz.tbi
ls -lh ../../genome/gencode.v35.chr_patch_hapl_scaff.genes_with_promoters.sorted.bed

echo "Running preprocess.sh..."
bash preprocess.sh

echo "Checking outputs..."
ls -lh wnn_meta_data.csv || true
ls -lh doubletfinder_inference.csv || true
ls -lh pbmc_granulocyte_sorted_10k_atac_fragments.sorted.bed || true
ls -lh pbmc_granulocyte_sorted_10k_atac_fragments.bedmap.gz || true

echo "Finished: $(date)"
