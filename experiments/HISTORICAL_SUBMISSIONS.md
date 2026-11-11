# Historical Slurm submissions

The following inventory records commands and resources from the November 10, 2026 audit.
Review these files as provenance. Use the experiment catalog for new launch plans.

**5. Complete Slurm submission-script inventory**

The recursive shell search found **230 shell files**. **93 contain Slurm directives or submission-related commands**, representing **71 distinct byte contents**. The inventory below lists all 93, including copies, generators, and scripts that merely reference submission directives.

For compactness:

- Resources are **CPUs / RAM / wall time**.
- `H100` means one H100 explicitly requested.
- `—` means no GPU request or no array directive.
- None of the listed batch-file headers specifies a partition. Partition selection therefore comes from submission flags/site defaults; actual live overrides are described separately.
- Log stems denote `.out` and `.err`, except where explicitly noted.
- Relative log paths are literal directives and depend on the submission working directory.

**Original independent checkout — seven historical batch files**

| Absolute script path | Job name; resources; array | Executes | Log stem |
|---|---|---|---|
| `/project/6001426/paa40/GLUE/GLUE/create_glue_env.sh` | `glue_env`; 4 / 16G / 6h; — | Environment creation and checks | `glue_env_%j` |
| `/project/6001426/paa40/GLUE/GLUE/install_glue_r_deps.sh` | `glue_r_deps`; 4 / 32G / 8h; — | Inline R dependency installation | `glue_r_deps_%j` |
| `/project/6001426/paa40/GLUE/GLUE/install_glue_r_deps_clean.sh` | `glue_r_clean`; 4 / 64G / 12h; — | Clean R dependency installation | `glue_r_clean_%j` |
| `/project/6001426/paa40/GLUE/GLUE/prepare_10x_glue_inputs.sh` | `prep_10x_glue`; 8 / 64G / 4h; — | Inline PBMC preparation | `prep_10x_glue_%j` |
| `/project/6001426/paa40/GLUE/GLUE/smoke_train_10x_glue.sh` | `smoke_10x_glue`; 8 / 64G / 4h; — | Inline original-GCN smoke training | `smoke_10x_glue_%j` |
| `/project/6001426/paa40/GLUE/GLUE/data/run_one_collect.sh` | `glue_collect_one`; 4 / 32G / 4h; — | Snakemake PBMC collection | `glue_collect_one_%j` |
| `/project/6001426/paa40/GLUE/GLUE/data/download/10x-Multiome-Pbmc10k/run_preprocess_10x_multiome.sh` | `preprocess_10x_multiome`; 8 / 64G / 6h; — | `bash preprocess.sh` | `preprocess_10x_multiome_%j` |

These are historical setup/smoke scripts, not active jobs.

**Reproduction branch — fourteen historical batch files**

These files live in `GLUE_Reproduction_View`, but their bodies generally execute against the main `GLUE` directory.

| Absolute script path | Job name; resources; array | Executes | Literal log stem |
|---|---|---|---|
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/data/download_all_glue_datasets.sh` | `glue_all_data`; 2 / 8G / 12h; — | Dataset downloads | `logs/glue_all_data_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/data/download_glue_datasets_array.sh` | `glue_dl`; 1 / 4G / 24h; `0-14%2` | Dataset download array | `logs/glue_dl_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/data/run_frags2rna_collect.sh` | `glue_frags2rna`; 8 / 128G / 48h; — | Four dataset collection targets | `../logs/glue_frags2rna_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/data/run_frags2rna_one_at_a_time.sh` | `glue_frag_one`; 4 / 64G / 8h; `0-3%1` | Serial fragment collection | `../logs/glue_frag_one_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/data/run_frags2rna_parallel_light.sh` | `glue_frag_light`; 4 / 64G / 8h; `0-3%4` | Parallel fragment collection | `../logs/glue_frag_light_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/data/validate_all_h5ad.sh` | `glue_validate_data`; 4 / 64G / 4h; — | Inline H5AD checks | `logs/glue_validate_data_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/data/validate_all_h5ad_backed.sh` | `glue_validate_backed`; 2 / 16G / 2h; — | Backed H5AD checks | `logs/glue_validate_backed_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/evaluation/run_eval_glue_one_target.sh` | `eval_glue_one`; 8 / 64G / 12h; — | One Snakemake target | `logs/eval_glue_one_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/evaluation/run_glue_250_500_array.sh` | `glue_250_500`; 8 / 64G / 3h30; `0-79%8` | Five datasets × two sizes × eight seeds | `logs/glue_250_500_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/evaluation/run_glue_official_array.sh` | `glue_official_eval`; 8 / 128G / 48h; `0-239%4` | Official GLUE subsampling targets | `logs/glue_official_eval_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/evaluation/run_glue_official_by_dataset_array.sh` | `glue_eval_ds`; 8 / 128G / 11h30; `0-4%5` | Official targets grouped by dataset | `logs/glue_eval_ds_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/r/setup_packrat_r.sh` | `glue_packrat`; 8 / 64G / 24h; — | Inline R/packrat setup | `logs/glue_packrat_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/training/smoke_train_10x_glue.sh` | `smoke_10x_glue`; 8 / 64G / 4h; — | Inline GCN smoke training | `logs/smoke_10x_glue_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_Reproduction_View/Run_On_fir/training/train_10x_full_glue.sh` | `glue_10x_full`; 16 / 128G / 24h; — | Inline full PBMC GCN training | `logs/glue_10x_full_%j` |

Several source `/project/6001426/paa40/GlUE_Exp/GLUE/Run_On_fir/activate_glue.sh`, which **does not currently exist**. These scripts require path repair before reuse.

**PBMC baseline, GAT comparison, and tuning — seventeen files**

For the first five rows, absolute logs are under `/project/6001426/paa40/GlUE_Exp/GLUE/logs/`.

| Absolute script path | Job/resources/array or wrapper behavior | Execution and status |
|---|---|---|
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/run_10x_gcn_reference.sh` | `gcn10x_ref`; 8 / 192G / 48h; H100; logs `gcn10x_ref_%j` | GCN reference via `workflow_gcn_10x`; historical complete |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/run_10x_gcn_subsamples.sh` | `gcn10x_sub`; same; `0-47`; logs `gcn10x_sub_%A_%a` | 48 GCN metric targets; complete |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/run_10x_gat_reference.sh` | `gat10x_ref`; 8 / 192G / 48h; H100; logs `gat10x_ref_%j` | GAT reference; historical complete, current path problem |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/run_10x_gat_subsamples.sh` | `gat10x_sub`; same; `0-47`; logs `gat10x_sub_%A_%a` | 48 GAT metric targets; historical complete, current path problem |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/collect_10x_gat_comparison.sh` | `gat10x_cmp`; 1 / 16G / 1h; logs `gat10x_cmp_corrected_%j` | Collects architecture comparison |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/run_10x_seed0_size250.sh` | `glue_10x_250`; 4 / 32G / 2h50; logs `../logs/glue_10x_250_%j` | Historical seed0 target |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/run_10x_size250_allseeds.sh` | `glue10x_250`; 4 / 32G / 2h50; `0-7%4`; logs `../logs/glue10x_250_%A_%a` | Historical eight-seed run |
| `/project/6001426/paa40/GlUE_Exp/GLUE/smoke_train_10x_gat.sh` | `gat_10x_smoke`; 8 / 64G / 4h; logs `logs/gat_10x_smoke_%j` | Inline GAT smoke; no GPU explicitly requested |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/gat_tuning_10x/screen_v1/run_one_config.sbatch` | `gat10x_tune`; 8 / 192G / 48h; H100 | Ten targets per configuration; superseded v1 |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/gat_tuning_10x/screen_v2/run_one_config.sbatch` | Same bytes/resources as v1 | v2 worker; partial completion |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/gat_tuning_10x/screen_v1/submit.sh` | Submits `0-9%2` by default | Logs in its `logs/%A_%a.{out,err}`; historical |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/gat_tuning_10x/screen_v2/submit.sh` | Same bytes; submits `0-9%2` | Logs in v2 `logs/`; repeated calls can submit another array |
| `/project/6001426/paa40/GlUE_Exp/GLUE/setup_10x_gat_evaluation.sh` | Generator | Generates reference/subsample/comparison launchers; does not itself establish execution |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/setup_10x_gcn_evaluation.sh` | Setup script; contains directive-search text | Constructs GCN evaluation setup |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/setup_gat_tuning_screen.sh` | Generator | Generates configuration workflows, worker, submit wrapper |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/repair_gat_tuning_screen_v2.sh` | Repair/generation script | Copies and repairs v1 setup into v2 |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/wait_and_launch_gat_manual_search.sh` | `srun --jobid=…` wrapper | Launches `run_gat_manual_search_in_allocation.sh` in an existing allocation |

The GAT workers pin an expected Git commit. Their current baseline checkout no longer has that historical GAT commit, so rerunning them unchanged would fail the pin check.

More seriously, `workflow_gat_10x/rules/methods.smk` invokes relative `workflow/scripts/run_GLUE.py`, while the current baseline runner does not accept `--graph-encoder`. The existing saved GAT results record GAT arguments, but **the current launcher/worktree combination cannot reproduce those commands unchanged**.

**SHARE architecture, matched subsampling, and dimensions — ten files**

Logs are under:

`/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/logs/`

| Absolute script path | Job; resources; array | Executes / log stem |
|---|---|---|
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/smoke.sbatch` | `share_smoke`; 8 / 64G / 2h; H100 | Smoke training; `smoke_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/rescue_smoke.sbatch` | `share_rescue`; 8 / 64G / 1h | Validate/evaluate existing smoke; `rescue_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/train_array.sbatch` | `share_train`; 8 / 192G / 48h; H100; `0-25%6` | `scripts/train_one.sh`; `train_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/evaluate_array.sbatch` | `share_metrics`; 8 / 64G / 24h; `0-25%6` | `evaluate_one.py`, gate extraction; `metrics_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/postprocess.sbatch` | `share_report`; 4 / 32G / 4h | `postprocess.py`; `report_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/matched_train_array.sbatch` | `share_match_train`; 8 / 192G / 48h; H100; `0-17%3` | `matched_train_one.sh`; `matched_train_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/matched_evaluate_array.sbatch` | `share_match_metrics`; 8 / 64G / 24h; `0-17%3` | `matched_evaluate_one.py`; `matched_metrics_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/matched_postprocess.sbatch` | `share_match_report`; 4 / 64G / 12h | `matched_postprocess.py`; `matched_report_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/slurm/full_dimension_smoke.sbatch` | `share_dim_smoke`; 8 / 192G / 2h; H100; `11,23,35` | Three 1024D smoke runs; `dimension_smoke_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/submit_all.sh` | Submission wrapper | Smoke validation, then training → `afterok` metrics → `afterok` report |

`submit_all.sh` does not guard against submitting a second complete workflow once smoke is valid. Training validation may skip completed outputs, but repeated calls still create duplicate jobs.

The full dimension experiment also used **inline `sbatch --wrap` submissions**, rather than a dedicated training `.sbatch` file. Their exact commands are preserved in:

[full_dimension_submitted_jobs_20260910.json](/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/full_dimension_submitted_jobs_20260910.json)

Recorded jobs:

| Job | Resources and partition | Payload |
|---|---|---|
| `59118632`, `share_dim_train` | H100, 8 CPUs, 32G, 12h; `gpubase_bygpu_b2`; 33 non-reused indices, `%6` | `scripts/full_dimension_train_one.sh` |
| `59118633`, `share_dim_metrics` | 8 CPUs, 64G, 12h; `cpubase_bycore_b2`; `0-35%6` | `full_dimension.py metrics` |
| `59118634`, `share_dim_report` | 4 CPUs, 32G, 4h; `cpubase_bycore_b2` | `full_dimension_report.py` |

Logs use `share_dim_train_%A_%a`, `share_dim_metrics_%A_%a`, and `share_dim_report_%A_%a` in the SHARE log directory.

**GATED experiments — fifteen batch files**

The `.slurm` log root is:

`/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/.slurm/`

| Absolute script path | Job; resources; array | Executes / log location |
|---|---|---|
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/run_10x_gated_full_reference.sh` | `gated10x_ref`; 8 / 192G / 48h; H100 | GATED `run_GLUE.py`; `.slurm/gated10x_ref_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/run_10x_gated_subsamples.sh` | `gated10x_sub`; same; `0-8` | Nine GATED subsets; `.slurm/gated10x_sub_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/collect_10x_gated_metrics.sbatch` | `gated10x_metrics`; 8 / 64G / 24h | Metrics collection shell; `.slurm/gated10x_metrics_%j` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/extract_gated_edge_analysis.sbatch` | `gated_edges`; 4 / 32G / 1h | `extract_gated_edge_analysis.py`; `evaluation/gate_analysis/slurm-%j.out`; stderr shares stdout |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/run_gated_tuning_stageA.sbatch` | `gated_tune_A`; 8 / 192G / 48h; H100; `0-14` | Stage A training/reuse; `.slurm/gated_tune_A_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/run_gated_tuning_stageA_metrics.sbatch` | `gated_tune_A_met`; 8 / 64G / 24h; `0-14` | Integration/combine metrics; `.slurm/gated_tune_A_met_%A_%a`; unused so far |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/run_gated_tuning_stageB.sbatch` | `gated_tune_B`; 8 / 192G / 48h; H100; array supplied externally | Finalist training/reuse; `.slurm/gated_tune_B_%A_%a`; planned |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/run_gated_tuning_stageB_metrics.sbatch` | `gated_tune_B_met`; 8 / 64G / 24h; array supplied externally | Finalist metrics; `.slurm/gated_tune_B_met_%A_%a`; planned |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep/run_dimension_train_array.sbatch` | `dimA_glue`; 8 / 192G / 48h; H100; `0-11%6` | Architecture-specific dimension training; `dimension_sweep/logs/train_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep/run_stageA_metrics.sbatch` | `dimA_metrics_fix`; 8 / 64G / 4h; `0-11%6` | Corrected 2k metrics; `dimension_sweep/logs/metrics_A_fix_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/dimension_sweep/run_8000_metrics.sbatch` | `dim8000_metrics`; 8 / 64G / 4h; `0-11%6` | 8k metrics; `dimension_sweep/logs/metrics_8000_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/gate_init_sensitivity/run_training.sbatch` | `gate_init_sens`; 8 / 192G / 48h; H100; `0-35%6` | Initialization training; `gate_init_sensitivity/logs/train_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/slurm/array_a.sbatch` | `share_gate_A`; 4 / 32G / 3h30; H100; `0-143` | `experiment.py run A`; `shareseq_gate_stability/logs/array_A_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/slurm/array_b.sbatch` | `share_gate_B`; 4 / 48G / **4h template**; H100; `0-47` | `experiment.py run B`; `shareseq_gate_stability/logs/array_B_%A_%a` |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/smoke_train_10x_gated.sh` | `gated_10x_smoke`; 8 / 32G / 1h | Inline gated smoke; `evaluation/.slurm/gated_10x_smoke_%j`; no GPU request |

Dimension and gate-sensitivity log paths in that table are relative to the absolute GATED `evaluation` directory.

Live SHARE B jobs override the four-hour template with **12 or 18 hours**. The source file alone does not describe their current resource requests.

**PBMC worktree — ten dedicated batch files**

All paths below are under the PBMC worktree; logs use the corresponding experiment’s `logs/` directory.

| Absolute script path | Job; resources; array | Payload / log stem / status |
|---|---|---|
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_perturbation/run_array.sbatch` | `pbmc_graph_gated`; 8 / 16G / 6h; H100; `0-17%3` | GATED graph perturbation runner; `train_%A_%a`; complete |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_perturbation/evaluate.sbatch` | `pbmc_graph_eval`; 8 / 48G / 6h | `scripts/evaluate.py`; `evaluate_%j`; complete |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/train_array.sbatch` | `pbmc_graph_gcn`; 8 / 16G / 6h; H100; `0-14%3` | `scripts/train.py`; `train_%A_%a`; task7 queued |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/evaluate.sbatch` | `pbmc_gcn_eval`; 8 / 48G / 6h | `scripts/evaluate.py`; `evaluate_%j`; waiting on task7 |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/smoke.sbatch` | `pbmc_gcn_smoke`; 8 / 16G / 45m; H100 | Bounded training/evaluation; `smoke_%j`; historical GPU alternative |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/smoke_cpu.sbatch` | `pbmc_gcn_smoke_cpu`; 8 / 16G / 1h | CPU smoke; `smoke_%j`; successful validation exists |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/submit_validated.sbatch` | `pbmc_gcn_submit`; 1 / 2G / 10m | `scripts/submit_pipeline.py`; `submit_%j`; dispatcher |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/train_array.sbatch` | `pbmc_gcn_random`; 8 / 16G / 6h; H100; `0-2%3` | Randomized `scripts/train.py`; `train_%A_%a`; complete |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/smoke_cpu.sbatch` | `pbmc_random_smoke`; 8 / 16G / 1h | Randomized CPU smoke; `smoke_%j`; complete |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/evaluate.sbatch` | `pbmc_gcn_combined`; 8 / 48G / 6h | Combined `scripts/evaluate.py`; `evaluate_%j`; waiting on task7 |

Original submissions recorded:

- GCN retention training `64840335`, evaluation `64840336`.
- Randomized training `64848480`, combined evaluation `64848481`.
- Original combined dependency: `afterok:64840335:64848480`.
- Current replacement evaluations `3088110` and `3088642` depend on `afterok:3069635`.

**PBMC worktree — thirteen byte-identical inherited GATED batch copies**

Every file below has the **same job name, resources, payload, and log directives as its corresponding GATED row above**. Several explicitly execute from `GLUE_GATED`; they are not isolated PBMC experiments.

```text
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/collect_10x_gated_metrics.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/dimension_sweep/run_8000_metrics.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/dimension_sweep/run_dimension_train_array.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/dimension_sweep/run_stageA_metrics.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/extract_gated_edge_analysis.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/gate_init_sensitivity/run_training.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/run_10x_gated_full_reference.sh
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/run_10x_gated_subsamples.sh
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/run_gated_tuning_stageA.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/run_gated_tuning_stageA_metrics.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/run_gated_tuning_stageB.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/run_gated_tuning_stageB_metrics.sbatch
/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/smoke_train_10x_gated.sh
```

Their status is **inherited duplicate / potentially misleading launcher**, not evidence of a second execution.

**Saved submitted scripts — seven copies**

| Absolute path | Byte-identical source |
|---|---|
| `/home/paa40/fir_job_audit/pending_pbmc_retry.sbatch` | PBMC GCN `train_array.sbatch` |
| `/home/paa40/glue_migration/batch/64840335.sbatch` | Same PBMC GCN script |
| `/home/paa40/fir_job_audit/submitted_share_62160949.sbatch` | SHARE `array_a.sbatch` |
| `/home/paa40/fir_job_audit/submitted_share_63134259.sbatch` | SHARE `array_a.sbatch` |
| `/home/paa40/fir_job_audit/submitted_share_3087784.sbatch` | SHARE `array_b.sbatch` |
| `/home/paa40/fir_job_audit/submitted_share_3087791.sbatch` | SHARE `array_b.sbatch` |
| `/home/paa40/fir_job_audit/submitted_share_64809374.sbatch` | SHARE `array_b.sbatch` |

These are provenance snapshots. Their source directives do not include all command-line overrides applied to the corresponding jobs.

**Additional wrappers, payloads, and embedded submission entrypoints**

These explain submission behavior that a `.sbatch`-only search would miss:

| Absolute path | Role |
|---|---|
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/submit.sh` | Runs prepare/preflight, then Python submission |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/experiment.py` | Submits A/B with a submission lock and saved job record |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/analyze.sh` | Executes gate-stability analysis; no submission |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/run.sh` | Prepare/test/submit command wrapper |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/scripts/submit_pipeline.py` | Submits training and dependent evaluation, using submission records |
| `/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/submit_pipeline.py` | Separate randomized training and combined evaluation |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/run_gat_manual_search_in_allocation.sh` | Executes `run_gat_manual_search.py`; no independent allocation |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/scripts/train_one.sh` | Architecture-specific training payload |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/scripts/matched_train_one.sh` | Matched-subsample training payload |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/scripts/full_dimension_train_one.sh` | Full dimension `--wrap` payload |
| `/project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/scripts/full_dimension_smoke_one.sh` | Dimension smoke payload |
| `/home/paa40/fir_job_audit/recover_share.py` | Historical recovery script containing the selective B25/B27 submission; not safe to rerun as an audit |

The inherited Snakemake profile at `evaluation/profiles/cls/config.yaml` also embeds `sbatch`. Its companion `cls.yaml` uses **`gaog_g1`, `cn_icg`, `gpu_4l`, and associated QoS names**. Those are inherited site settings, not the Fir resource configuration used by the audited jobs. Copies exist in all seven checkouts.

The remaining shell files are preprocessing, environment-export, packaging, target-generation, and analysis helpers; their presence is not submission evidence. I also inspected branch-tip shell inventories and historical deletions; no additional deleted submission-script paths were returned by the Git deletion search.

## SHARE full-dimension command records

The command snapshot below preserves the effective arguments, including options supplied outside the batch scripts.

```json
{
  "training": "59118632",
  "metrics": "59118633",
  "report": "59118634"
}
```

## Pending array and evaluation overrides at preservation

These rows record the actual scheduler fields. Batch headers alone do not describe the resources requested.

| Job | Array indices | Time | Partition | Dependency | Command |
|---|---|---|---|---|---|
| 3069635 | 7 | 06:00:00 | gpubase_bygpu_b2,gpubackfill | (null) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/train_array.sbatch |
| 3087784 | 28 | 12:00:00 | gpubase_bygpu_b2,gpubackfill | (null) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/slurm/array_b.sbatch |
| 3087791 | 36 | 18:00:00 | gpubase_bygpu_b3,gpubackfill | (null) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/slurm/array_b.sbatch |
| 3088110 | — | 06:00:00 | cpubase_bycore_b2,cpubackfill,c12hbackfill | afterok:3069635_*(unfulfilled) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/evaluate.sbatch |
| 3088642 | — | 06:00:00 | cpubase_bycore_b2,cpubackfill,c12hbackfill | afterok:3069635_*(unfulfilled) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/randomized_control/evaluate.sbatch |
| 3121477 | 25,27%2 | 12:00:00 | gpubase_bygpu_b2,gpubackfill | (null) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/slurm/array_b.sbatch |
| 62160949 | 110-143 | 03:30:00 | gpubase_bygpu_b2,gpubackfill | (null) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/slurm/array_a.sbatch |
| 63134259 | 21 | 03:30:00 | gpubase_bygpu_b2,gpubackfill | (null) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/slurm/array_a.sbatch |
| 64809374 | 32 | 12:00:00 | gpubase_bygpu_b2,gpubackfill | (null) | /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/slurm/array_b.sbatch |

The two CPU evaluations depend on the successful completion of PBMC task 7. SHARE B uses the recorded 12-hour and 18-hour overrides.
