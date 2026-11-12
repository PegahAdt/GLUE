# Result and figure index

Scientific outputs remain in external storage. This directory is documentation, not a write target: the launcher refuses outputs inside a code checkout. Paths below are historical contracts from the dated audits, not publicly downloadable artifacts or proof of completion. No checkpoint, dataset, log or thesis figure was copied or recomputed. The small existing 8,000-cell metric YAMLs remain byte-identical under [evaluation/dimension_sweep/metrics_8000_runs](../evaluation/dimension_sweep/metrics_8000_runs).

Historical aliases: `B` denotes the original Fir GLUE checkout; full absolute paths remain in the immutable manifests. `<output_root>` is a separately configured fresh external directory. See each linked experiment source/configuration for exact run IDs.

## pbmc_gcn_comparison

<output_root>/pbmc_gcn_comparison/runs/<task_id> and metrics/<task_id>; historical B/evaluation/results_gcn_h100/raw/10x-Multiome-Pbmc10k/

Plot/report source: [evaluation/collect_10x_gcn_gat_gated_comparison.py](../evaluation/collect_10x_gcn_gat_gated_comparison.py)<br>[evaluation/generate_gcn_gat_gated_metric_comparisons.py](../evaluation/generate_gcn_gat_gated_metric_comparisons.py)<br>[evaluation/compare_10x_gcn_vs_gat.py](../evaluation/compare_10x_gcn_vs_gat.py)<br>[evaluation/analyze_10x_gcn_vs_gat_statistics.py](../evaluation/analyze_10x_gcn_vs_gat_statistics.py).

Historical audit: 48 subsets evaluated + full reference. No new runtime reproduction.

## pbmc_gat_comparison

<output_root>/pbmc_gat_comparison/runs/<task_id> and metrics/<task_id>; historical B/evaluation/results_gat/raw/10x-Multiome-Pbmc10k/

Plot/report source: [evaluation/collect_10x_gcn_gat_gated_comparison.py](../evaluation/collect_10x_gcn_gat_gated_comparison.py)<br>[evaluation/generate_gcn_gat_gated_metric_comparisons.py](../evaluation/generate_gcn_gat_gated_metric_comparisons.py)<br>[evaluation/compare_10x_gcn_vs_gat.py](../evaluation/compare_10x_gcn_vs_gat.py)<br>[evaluation/analyze_10x_gcn_vs_gat_statistics.py](../evaluation/analyze_10x_gcn_vs_gat_statistics.py).

Historical audit: 48 subsets evaluated + full reference; historical GAT Snakemake binding broken. No new runtime reproduction.

## pbmc_gated_comparison

<output_root>/pbmc_gated_comparison/runs/<task_id> and metrics/<task_id>; historical /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/results_gated/raw/10x-Multiome-Pbmc10k/

Plot/report source: [evaluation/collect_10x_gcn_gat_gated_comparison.py](../evaluation/collect_10x_gcn_gat_gated_comparison.py)<br>[evaluation/generate_gcn_gat_gated_metric_comparisons.py](../evaluation/generate_gcn_gat_gated_metric_comparisons.py)<br>[evaluation/compare_10x_gcn_vs_gat.py](../evaluation/compare_10x_gcn_vs_gat.py)<br>[evaluation/analyze_10x_gcn_vs_gat_statistics.py](../evaluation/analyze_10x_gcn_vs_gat_statistics.py).

Historical audit: 9 subsets evaluated + full reference. No new runtime reproduction.

## pbmc_gat_tuning

<output_root>/pbmc_gat_tuning/{runs,metrics}/<task_id>; historical B/evaluation/results_gat_tuning/screen_v2/<config>/raw/…

Plot/report source: [evaluation/generate_gat_tuning_metrics_tex.py](../evaluation/generate_gat_tuning_metrics_tex.py)<br>[evaluation/generate_best_gat_vs_gcn_metrics_tex.py](../evaluation/generate_best_gat_vs_gcn_metrics_tex.py).

Historical audit: v2: 97/100 requested targets; three missing; v1 no requested outputs. No new runtime reproduction.

## pbmc_gat_manual

O/evaluation/results_gat_manual_search/<candidate>/<size-and-seed>/…; search_summary.json is intended winner record.

Plot/report source: Not applicable / no entry point identified.

Adaptive plan/source retained; finalized execution and feature-reference policy unresolved.

## pbmc_gated_tuning

<output_root>/pbmc_gated_tuning/{runs,metrics}/<task_id>; historical /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/results_gated_tuning/stageA/<tag>/

Plot/report source: [evaluation/collect_gated_tuning_stageA.py](../evaluation/collect_gated_tuning_stageA.py).

Historical audit: 15 Stage A configurations: 14 trained + one reused baseline; metrics not run; Stage B not designed. No new runtime reproduction.

## pbmc_dimensions

<output_root>/pbmc_dimensions/{runs,metrics}/<task_id>; historical /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/results_dimension_sweep/architecture:<arch>/dim:<d>/subsample_size:<n>-subsample_seed:0/model_seed:0; summary files under evaluation/dimension_sweep/.

Plot/report source: [evaluation/dimension_sweep/generate_dimension_model_report.py](../evaluation/dimension_sweep/generate_dimension_model_report.py)<br>[evaluation/dimension_sweep/generate_combined_report.py](../evaluation/dimension_sweep/generate_combined_report.py).

30 registered conditions: 24 non-50D and six reused 50D references. Registry correction complete; no fresh GPU reproduction.

## pbmc_gate_initialization

Historical new fits: /project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/results_gate_init_sensitivity/gate_init:<g>/subsample_size:<n>-subsample_seed:<s>/model_seed:0; .95 reused references: GLUE_GATED/evaluation/results_gated/raw/10x-Multiome-Pbmc10k/... . Distribution/metric reports: /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/gate_init_sensitivity_{report,metrics}/. Clean future runs/metrics use <output_root>/pbmc_gate_initialization/.

Plot/report source: [evaluation/gate_init_sensitivity_metrics/analyze_gate_init_metrics.py](../evaluation/gate_init_sensitivity_metrics/analyze_gate_init_metrics.py)<br>[evaluation/gate_init_sensitivity_report/analyze_gate_init_distributions.py](../evaluation/gate_init_sensitivity_report/analyze_gate_init_distributions.py).

Historical audit: 45 evaluated configurations; nine reused + 36 fresh. No new runtime reproduction.

## pbmc_gate_analysis

G/evaluation/gate_analysis/: gates_<model>.csv, gate_distribution_summary.csv, ranked/suppressed-edge/correlation tables, gate_stability_size*.csv and TeX report.

Plot/report source: [evaluation/gate_analysis/build_gated_edge_analysis_report.py](../evaluation/gate_analysis/build_gated_edge_analysis_report.py).

Historical audit: Ten reused models analyzed; generated reports excluded. No new runtime reproduction.

## share_primary

<output_root>/share_primary/{runs,metrics}/<task_id>; historical B/evaluation/shareseq_ma2020/results/<run_id>; metrics/, analysis/, reports/ under the same historical experiment root.

Plot/report source: [evaluation/shareseq_ma2020/scripts/postprocess.py](../evaluation/shareseq_ma2020/scripts/postprocess.py)<br>[evaluation/shareseq_ma2020/scripts/build_current_results_report.py](../evaluation/shareseq_ma2020/scripts/build_current_results_report.py).

Historical audit: 26 trained and evaluated. No new runtime reproduction.

## share_matched_cells

<output_root>/share_matched_cells/{runs,metrics}/<task_id>; historical B/evaluation/shareseq_ma2020/results/<run_id>; metrics/, analysis/, reports/ under the same historical experiment root.

Plot/report source: [evaluation/shareseq_ma2020/scripts/matched_postprocess.py](../evaluation/shareseq_ma2020/scripts/matched_postprocess.py).

Dated audit: 18 checkpoint paths; nine GAT metric files and no matching GCN metric files. Evaluation incomplete.

## share_dimensions

<output_root>/share_dimensions/{runs,metrics}/<task_id>; historical B/evaluation/shareseq_ma2020/results/<run_id>; metrics/, analysis/, reports/ under the same historical experiment root.

Plot/report source: [evaluation/shareseq_ma2020/scripts/full_dimension_report.py](../evaluation/shareseq_ma2020/scripts/full_dimension_report.py).

Historical audit: 36 validated metric directories; three reused 50D. No new runtime reproduction.

## share_gate_stability

/project/6001426/paa40/GlUE_Exp/GLUE_GATED/evaluation/shareseq_gate_stability/dim_<d>/gateinit_<p>/seed_<s>/; analysis destination supplied to analyze.py.

Plot/report source: [evaluation/shareseq_gate_stability/analyze.py](../evaluation/shareseq_gate_stability/analyze.py).

192 planned conditions; 139 retained checkpoint paths and matching Python-version/job provenance in the dated audits. Aggregate analysis incomplete; frozen portability blocked.

## pbmc_gated_graph

/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_perturbation/results/10x-Multiome-Pbmc10k/<condition>/graph_seed:0/model_seed:<s>; reports/full/{per_run_metrics,summary_metrics,baseline_comparison,metric_availability,graph_statistics}.csv plus figures/report. Randomized GCN run directories actually live in the parent original-GCN results tree, as recorded in its manifest.

Plot/report source: [evaluation/pbmc_graph_perturbation/scripts/reporting.py](../evaluation/pbmc_graph_perturbation/scripts/reporting.py).

Historical audit: 18 trained and evaluated. No new runtime reproduction.

## pbmc_gcn_graph_subsampling

/project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/results/10x-Multiome-Pbmc10k/<condition>/graph_seed:0/model_seed:<s>; reports/full/{per_run_metrics,summary_metrics,baseline_comparison,metric_availability,graph_statistics}.csv plus figures/report. Randomized GCN run directories actually live in the parent original-GCN results tree, as recorded in its manifest.

Plot/report source: [evaluation/pbmc_graph_subsampling_gcn/scripts/gcn_report.py](../evaluation/pbmc_graph_subsampling_gcn/scripts/gcn_report.py).

15 registered conditions; 14 checkpoint paths in the dated audit. Frozen pipeline; no fresh reproduction.

## pbmc_gcn_randomized

Checkpoints: /project/6001426/paa40/GlUE_Exp/GLUE_GATED_PBMC/evaluation/pbmc_graph_subsampling_gcn/results/10x-Multiome-Pbmc10k/randomized/graph_seed:0/model_seed:<s>/. Evaluator default: randomized_control/reports/full. Preserved batch explicitly overrides output to the parent pbmc_graph_subsampling_gcn/reports/combined_randomized_job_<SLURM_JOB_ID>/.

Plot/report source: [evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/gcn_report.py](../evaluation/pbmc_graph_subsampling_gcn/randomized_control/scripts/gcn_report.py).

Historical audit: 3/3 trained; combined18-run evaluation waits on retention task7. No new runtime reproduction.

## pbmc_historical_smoke

Eight compact size-250 metric YAMLs from the distinct original reproduction branch are preserved under [historical/reproduction/metrics](../historical/reproduction/metrics); they are historical evidence, not new independent thesis conditions.

Historical original checkout data/dataset/*-glue-ready.h5ad and smoke output paths; B/evaluation/results*/raw/…; curated reproduction-view metrics are external to these three clean trees.

Plot/report source: [evaluation/print_completed_latex_table.py](../evaluation/print_completed_latex_table.py).

Historical audit: Original 1000-cell smoke and baseline smoke/full/GAT smoke artifacts exist; size250 eight seeds evaluated. No new runtime reproduction.

## gat_normalized

No experiment-specific output contract identified; generic runner could emit standard latents/checkpoints if a design were created.

Plot/report source: Not applicable / no entry point identified.

Implementation and test source only; no verified thesis experiment manifest or results.

## upstream_suites

O/evaluation/results/{raw,*.csv,*.pdf,umap_grid}; case studies emit stage directories under O/experiments/<case>/.

Plot/report source: [evaluation/workflow/scripts/benchmark.R](../evaluation/workflow/scripts/benchmark.R).

Historical audit: Configured source; no verified local case-study model outputs. No new runtime reproduction.

## pbmc_gated_stageB_plan

Historical GLUE_GATED/evaluation/results_gated_tuning/stageB/<tag>/

Plot/report source: [evaluation/select_gated_tuning_stageA.py](../evaluation/select_gated_tuning_stageA.py).

Plan only: finalized selector output and approved finalist conditions not established.

## upstream_hyperparam

O/evaluation/results/raw/<dataset>/<data_conf>/<prior_conf>/<method>/<hyperparam_conf>/seed:<seed>; results/hyperparam.csv and metric PDFs.

Plot/report source: [evaluation/workflow/hyperparam.smk](../evaluation/workflow/hyperparam.smk)<br>[evaluation/workflow/scripts/hyperparam.R](../evaluation/workflow/scripts/hyperparam.R).

Historical audit: Configured inherited source; local completion not established.. No new runtime reproduction.

## upstream_hvg

O/evaluation/results/raw/<dataset>/<data_conf>/<prior_conf>/<method>/<hyperparam_conf>/seed:<seed>; results/hvg.csv and metric PDFs.

Plot/report source: [evaluation/workflow/hvg.smk](../evaluation/workflow/hvg.smk)<br>[evaluation/workflow/scripts/hvg.R](../evaluation/workflow/scripts/hvg.R).

Historical audit: Configured inherited source; local completion not established.. No new runtime reproduction.

## upstream_benchmark

O/evaluation/results/raw/<dataset>/<data_conf>/<prior_conf>/<method>/<hyperparam_conf>/seed:<seed>; results/benchmark.csv and metric PDFs.

Plot/report source: [evaluation/workflow/benchmark.smk](../evaluation/workflow/benchmark.smk)<br>[evaluation/workflow/scripts/benchmark.R](../evaluation/workflow/scripts/benchmark.R).

Historical audit: Configured inherited source; local completion not established.. No new runtime reproduction.

## upstream_benchmark_noprep

O/evaluation/results/raw/<dataset>/<data_conf>/<prior_conf>/<method>/<hyperparam_conf>/seed:<seed>; results/benchmark_noprep.csv and metric PDFs.

Plot/report source: [evaluation/workflow/benchmark_noprep.smk](../evaluation/workflow/benchmark_noprep.smk)<br>[evaluation/workflow/scripts/benchmark.R](../evaluation/workflow/scripts/benchmark.R).

Historical audit: Configured inherited source; local completion not established.. No new runtime reproduction.

## upstream_prior_corrupt

O/evaluation/results/raw/<dataset>/<data_conf>/<prior_conf>/<method>/<hyperparam_conf>/seed:<seed>; results/prior_corrupt.csv and metric PDFs.

Plot/report source: [evaluation/workflow/prior_corrupt.smk](../evaluation/workflow/prior_corrupt.smk)<br>[evaluation/workflow/scripts/prior_corrupt.R](../evaluation/workflow/scripts/prior_corrupt.R).

Historical audit: Configured inherited source; local completion not established.. No new runtime reproduction.

## upstream_prior_alt

O/evaluation/results/raw/<dataset>/<data_conf>/<prior_conf>/<method>/<hyperparam_conf>/seed:<seed>; results/prior_alt.csv and metric PDFs.

Plot/report source: [evaluation/workflow/prior_alt.smk](../evaluation/workflow/prior_alt.smk)<br>[evaluation/workflow/scripts/prior_alt.R](../evaluation/workflow/scripts/prior_alt.R).

Historical audit: Configured inherited source; local completion not established.. No new runtime reproduction.

## upstream_subsample

O/evaluation/results/raw/<dataset>/<data_conf>/<prior_conf>/<method>/<hyperparam_conf>/seed:<seed>; results/subsample.csv and metric PDFs.

Plot/report source: [evaluation/workflow/subsample.smk](../evaluation/workflow/subsample.smk)<br>[evaluation/workflow/scripts/subsample.R](../evaluation/workflow/scripts/subsample.R).

Historical audit: Configured inherited source; local completion not established.. No new runtime reproduction.

## case_atlas

O/experiments/Atlas/<stage>/ with final.dill/H5AD/CSV/PDF/HTML as declared in Snakefile and paired notebook source; OverCorrection final integration_consistency.pdf.

Plot/report source: [experiments/Atlas/s06_sankey.py](../experiments/Atlas/s06_sankey.py)<br>[experiments/Atlas/e03_visualize.py](../experiments/Atlas/e03_visualize.py)<br>[experiments/Atlas/scalability.R](../experiments/Atlas/scalability.R).

Historical audit: Preserved upstream source; no local completion established.. No new runtime reproduction.

## case_reginf

O/experiments/RegInf/<stage>/ with final.dill/H5AD/CSV/PDF/HTML as declared in Snakefile and paired notebook source; OverCorrection final integration_consistency.pdf.

Plot/report source: [experiments/RegInf/s06_genomic_tracks.py](../experiments/RegInf/s06_genomic_tracks.py)<br>[experiments/RegInf/s07_violin.py](../experiments/RegInf/s07_violin.py).

Historical audit: Preserved upstream source; no local completion established.. No new runtime reproduction.

## case_tripleomics

O/experiments/TripleOmics/<stage>/ with final.dill/H5AD/CSV/PDF/HTML as declared in Snakefile and paired notebook source; OverCorrection final integration_consistency.pdf.

Plot/report source: [experiments/TripleOmics/s03_markers.py](../experiments/TripleOmics/s03_markers.py)<br>[experiments/TripleOmics/s04_reg_contrib.py](../experiments/TripleOmics/s04_reg_contrib.py)<br>[experiments/TripleOmics/s05_clusterability.py](../experiments/TripleOmics/s05_clusterability.py)<br>[experiments/TripleOmics/e02_comparison.py](../experiments/TripleOmics/e02_comparison.py).

Historical audit: Preserved upstream source; no local completion established.. No new runtime reproduction.

## case_batcheffect

O/experiments/BatchEffect/<stage>/ with final.dill/H5AD/CSV/PDF/HTML as declared in Snakefile and paired notebook source; OverCorrection final integration_consistency.pdf.

Plot/report source: [experiments/BatchEffect/Ma-2020.py](../experiments/BatchEffect/Ma-2020.py)<br>[experiments/BatchEffect/Muto-2021.py](../experiments/BatchEffect/Muto-2021.py)<br>[experiments/BatchEffect/Yao-2021.py](../experiments/BatchEffect/Yao-2021.py).

Historical audit: Preserved upstream source; no local completion established.. No new runtime reproduction.

## case_overcorrection

O/experiments/OverCorrection/<stage>/ with final.dill/H5AD/CSV/PDF/HTML as declared in Snakefile and paired notebook source; OverCorrection final integration_consistency.pdf.

Plot/report source: [experiments/OverCorrection/plot.py](../experiments/OverCorrection/plot.py).

Historical audit: Preserved upstream source; no local completion established.. No new runtime reproduction.

## share_primary_gate_initialization

<output_root>/share_primary/{runs,metrics}/<task_id>; historical B/evaluation/shareseq_ma2020/results/<run_id>; metrics/, analysis/, reports/ under the same historical experiment root.

Plot/report source: [evaluation/shareseq_ma2020/scripts/postprocess.py](../evaluation/shareseq_ma2020/scripts/postprocess.py)<br>[evaluation/shareseq_ma2020/scripts/build_current_results_report.py](../evaluation/shareseq_ma2020/scripts/build_current_results_report.py).

Historical audit: 26 trained and evaluated. No new runtime reproduction.

## share_primary_gated_cells

<output_root>/share_primary/{runs,metrics}/<task_id>; historical B/evaluation/shareseq_ma2020/results/<run_id>; metrics/, analysis/, reports/ under the same historical experiment root.

Plot/report source: [evaluation/shareseq_ma2020/scripts/postprocess.py](../evaluation/shareseq_ma2020/scripts/postprocess.py)<br>[evaluation/shareseq_ma2020/scripts/build_current_results_report.py](../evaluation/shareseq_ma2020/scripts/build_current_results_report.py).

Historical audit: 26 trained and evaluated. No new runtime reproduction.

## share_graph_retention_unlocated

No dedicated manifest, checkpoint/result mapping or retention-fraction output contract identified in inspected trees.

Plot/report source: Not applicable / no entry point identified.

No dedicated SHARE guidance-edge-retention design or result located. Do not substitute a cell-subsampling experiment.
