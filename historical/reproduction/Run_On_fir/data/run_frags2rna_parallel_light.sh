#!/bin/bash
#SBATCH --job-name=glue_frag_light
#SBATCH --time=8:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4
#SBATCH --array=0-3%4
#SBATCH --output=../logs/glue_frag_light_%A_%a.out
#SBATCH --error=../logs/glue_frag_light_%A_%a.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE
mkdir -p logs

source activate_glue.sh

cd /project/6001426/paa40/GlUE_Exp/GLUE/data

TARGETS=(
  collect/Ma-2020.html
  collect/10x-Multiome-Pbmc10k.html
  collect/Muto-2021.html
  collect/Yao-2021.html
)

target="${TARGETS[$SLURM_ARRAY_TASK_ID]}"

echo "Running target: $target"
echo "Array task: $SLURM_ARRAY_TASK_ID"
echo "Node: $SLURMD_NODENAME"
date

snakemake --nolock -j1 -pr "$target"

echo "Finished target: $target"
date
