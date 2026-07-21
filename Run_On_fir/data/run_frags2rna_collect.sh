#!/bin/bash
#SBATCH --job-name=glue_frags2rna
#SBATCH --time=48:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=8
#SBATCH --output=../logs/glue_frags2rna_%j.out
#SBATCH --error=../logs/glue_frags2rna_%j.err

set -eo pipefail

cd /project/6001426/paa40/GlUE_Exp/GLUE/data
mkdir -p ../logs

source ../activate_glue.sh

snakemake -j1 -pr \
  collect/Ma-2020.html \
  collect/10x-Multiome-Pbmc10k.html \
  collect/Muto-2021.html \
  collect/Yao-2021.html
