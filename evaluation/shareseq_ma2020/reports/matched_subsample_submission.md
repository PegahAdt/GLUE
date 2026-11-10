# Matched GCN/GAT subsample submission

Training: `58768924` (18 tasks, concurrency 3). Metrics: `58768939`, dependency `afterok:58768924:58723588`. Architecture-by-size report: `58768984`, dependency `afterok:58768939:58723588`. Original jobs 58723587/58723588/58723589 and their manifest/scripts were left unchanged.

All 18 output directories were absent immediately before submission. The nine existing manifests were verified against both existing GATED H5AD observation orders. New runs materialize in that exact order and check it before training. Graph SHA256: `4eb79675fa9c2de1d62356a3cc9d92eeecfea00ba9ddcf267c3cab6127495637`. Shared parameters and validated entry points are unchanged; latent_dim=50, model_seed=0, GAT negative_slope=0.2.

Metrics use the exact paths from each GATED run’s unirep_inputs.json after original metrics completion. No PCA/LSI computation is present in the new evaluator. Feature consistency is computed by the canonical script relative to the same-architecture full-data primary model.

| Array index | Run ID | Reused cell manifest |
|---|---|---|
| 0 | gcn_size8000_subsample0_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size8000_seed0.txt |
| 1 | gat_size8000_subsample0_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size8000_seed0.txt |
| 2 | gcn_size8000_subsample1_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size8000_seed1.txt |
| 3 | gat_size8000_subsample1_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size8000_seed1.txt |
| 4 | gcn_size8000_subsample2_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size8000_seed2.txt |
| 5 | gat_size8000_subsample2_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size8000_seed2.txt |
| 6 | gcn_size16000_subsample0_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size16000_seed0.txt |
| 7 | gat_size16000_subsample0_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size16000_seed0.txt |
| 8 | gcn_size16000_subsample1_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size16000_seed1.txt |
| 9 | gat_size16000_subsample1_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size16000_seed1.txt |
| 10 | gcn_size16000_subsample2_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size16000_seed2.txt |
| 11 | gat_size16000_subsample2_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size16000_seed2.txt |
| 12 | gcn_size24000_subsample0_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size24000_seed0.txt |
| 13 | gat_size24000_subsample0_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size24000_seed0.txt |
| 14 | gcn_size24000_subsample1_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size24000_seed1.txt |
| 15 | gat_size24000_subsample1_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size24000_seed1.txt |
| 16 | gcn_size24000_subsample2_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size24000_seed2.txt |
| 17 | gat_size24000_subsample2_model0 | /project/6001426/paa40/GlUE_Exp/GLUE/evaluation/shareseq_ma2020/manifests/cells_size24000_seed2.txt |

All new training tasks request one H100, 192 GB host RAM, 8 CPUs, and 48 hours. GAT retains the full guidance graph at every cell size, so reducing cell count does not necessarily reduce attention memory or runtime proportionally. Concurrency is capped at three.

The analysis reads `architecture_by_size_manifest.csv` (30 runs), writes all requested mean ± sample SD summaries and paired differences under `metrics/architecture_by_size_*`, and runtime scaling under `analysis/architecture_runtime_scaling.*`. Final report: `reports/architecture_by_size_report.md`. Full-data endpoints are gcn_sizefull_model0, gat_sizefull_model0, and gated_sizefull_model0_gate0.95; each has n=1 and no across-subsample SD. Numerical results are pending completion of the dependent jobs.
