# Run_On_fir

This folder contains the custom scripts/config files added to run GLUE on Fir.

Original GLUE source files are kept in the repo root and original folders.

## Main files

- `activate_glue.sh`: activates the local GLUE micromamba environment.
- `env/env.original.yaml`: backup of original GLUE environment file.
- `env/env.conda-only.yaml`: working modified environment file.
- `data/download_glue_datasets_array.sh`: downloads official preprocessed datasets.
- `data/validate_all_h5ad_backed.sh`: validates `.h5ad` files safely in backed mode.
- `training/smoke_train_10x_glue.sh`: small GLUE smoke test.
- `training/train_10x_full_glue.sh`: full 10x Multiome PBMC GLUE training.
- `evaluation/make_glue_official_targets.sh`: creates 240 official GLUE-only evaluation targets.
- `evaluation/run_eval_glue_one_target.sh`: runs one official GLUE evaluation target.
- `evaluation/run_glue_250_b1_array.sh`: short partition-specific evaluation array for size-250 targets.
- `r/setup_packrat_r.sh`: R/packrat setup attempt.

## Do not commit

Do not commit large/generated folders:

- `conda/`
- `data/dataset/`
- `results/`
- `evaluation/results/`
- `logs/`
- `r-lib/`

## Extra files

- `export_env.sh`: helper for exporting/inspecting the environment.
- `data/run_frags2rna_collect.sh`: earlier FRAGS2RNA collection script.
- `data/run_frags2rna_one_at_a_time.sh`: FRAGS2RNA script variant that runs one notebook/task at a time.
- `data/run_frags2rna_parallel_light.sh`: lighter parallel FRAGS2RNA script variant.
- `evaluation/glue_official_targets.txt`: organized copy of the 240 official GLUE-only target list.
- `evaluation/glue_targets_250_500.txt`: organized copy of the size-250 and size-500 target subset.
