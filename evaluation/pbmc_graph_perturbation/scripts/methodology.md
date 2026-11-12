# Evaluation methodology

All metrics operate on saved, unnormalized 50-dimensional latent coordinates with Euclidean distance. No model is trained or updated. All 18 RNA/ATAC embeddings are validated against their source identifier sets and reordered by unique source cell ID. Nonfinite values, duplicated IDs, missing cells, differing dimensions, mismatched manifests and metadata are errors, not silently discarded observations. Feature embeddings are checked against the reconstructed graph node set and latent dimension. Random evaluation seed is 0 by default, independent of model and graph seeds.

## Source evidence and annotation validity

`data/collect/10x-Multiome-Pbmc10k.ipynb` reads one 10x Multiome feature/barcode matrix and splits its gene-expression and peak columns. Both assays receive the same metadata barcode subset and singlet mask. Evaluation requires that provenance, matching unique source barcode sets, the expected Multiome protocol/dataset and identical sample identifiers before computing paired metrics. Source notebook hash and evidence are written to `pairing_verification.json`. CSV row order alone never establishes pairing. The same biological cell can have matching source IDs even though GLUE was trained as an unpaired integration model.

Cell types are 19 annotated joint Seurat WNN cluster labels from `data/download/10x-Multiome-Pbmc10k/wnn.r`, joined by barcode in the collection notebook. These reference annotations use both assays and are not independent biological ground truth. `domain` describes modality; the sample identifier `orig.ident` is constant (`SeuratProject`). No independent donor or batch effect can be assessed. Neither modality nor cluster IDs are substituted for missing biological cell types.

## Paired alignment

For N verified pairs `(x_i,y_i)`, directional FOSCTTM is `mean_i[sum_j 1(d(x_i,y_j)<d(x_i,y_i))/N]`. The reverse direction is also computed; the reported overall FOSCTTM averages both directions. Smaller is better. Strict inequality and denominator N exactly match `scglue.metrics.foscttm`. Including the true counterpart in the denominator makes the maximum `(N-1)/N`. Exact Euclidean distances are evaluated in blocks, with no N-by-N distance matrix retained.

Matching recall@k is the fraction of anchors with the true counterpart among the k nearest target cells, computed in each direction and averaged. Higher is better. Exact ties are broken by target index after ID alignment; FOSCTTM does not count tied distances as closer. Partial barcode correspondence is not guessed; paired metrics become N/A when the supported provenance fails.

## Cross-modal structure and label transfer

Cross-modal MNN uses k=15 neighbors in the opposite modality (capped at available cells). A pair is mutual if each endpoint appears in the other's cross-modal neighbor set. Report unique pair count, anchor coverage in each assay, and `2*mutual_pairs/(RNA_directed_edges+ATAC_directed_edges)`. These are descriptive overlap quantities; more MNN pairs do not universally imply better biological integration. MNN cell-type agreement measures the fraction of mutual pairs sharing reference type.

Cross-modal nearest-neighbor cell-type agreement uses the single nearest target and averages the two directional agreements. Label transfer uses uniform 15-NN majority vote, with alphabetically ordered labels breaking vote ties. Report accuracy, macro-F1 (zero for undefined precision/recall), and balanced accuracy (mean recall over true classes) in both directions. No parameter is tuned using labels. True paired counterparts remain in the target pool; transfer is reference annotation concordance, not held-out predictive validation. Label agreement is potentially optimistic because both assays share WNN-derived annotations.

## Biological conservation and modality mixing

Raw biological ASW is the standard silhouette `s_i=(b_i-a_i)/max(a_i,b_i)`, range [-1,1], using reference cell types. Higher is better. `avg_silhouette_width=(mean(s)+1)/2` matches GLUE's scaled [0,1] convention. Both values are reported; all cells are used in full evaluation. sklearn's pairwise calculations obey a configured 64 MiB working-memory target.

Within-cell-type modality ASW is `mean_type mean_cells(1-|s_i|)` with silhouette grouping by modality. Higher means less assay separation, not necessarily better biology. Types that cannot support silhouette (fewer than two modality groups or one group per cell) are excluded and eligible cell fraction is recorded; unlike legacy GLUE, degenerate groups are not assigned perfect mixing. Global raw modality ASW is also descriptive and is not directly treated as a biological score. There is no independent-batch ASW.

Cell-type MAP, Seurat alignment score and neighbor conservation call `scglue.metrics` directly. MAP uses neighbor fraction .01 and same-label average precision. Seurat alignment uses .01 neighbor fraction, 4 repeats and evaluation seed 0; it balances the modality cell counts. It evaluates assay mixing, not independent batch correction.

Graph connectivity follows GLUE's exact definition: Scanpy neighbors on latent coordinates, k=15, no PCA, Euclidean, seed 0; mean across reference types of the largest strongly connected component fraction in each type's induced connectivity graph. The connectivity matrix is symmetric in this workflow. The shared neighbor graph is reused for clustering rather than recomputed unnecessarily.

## Clustering

Leiden clustering uses Scanpy's weighted neighbor-connectivity graph, default fixed resolution 1.0, evaluation seed 0. NMI uses sklearn's arithmetic normalization `2*MI/(H(labels)+H(clusters))`; ARI is the chance-adjusted Rand index. Higher is better; ARI may be negative. Additionally, the legacy GLUE NMI procedure searches resolutions 0.1,0.2,...,2.0 and reports maximum NMI. The chosen resolution and ARI at that same resolution are recorded. This label-selected maximum is optimistic and exploratory; it is distinct from fixed-resolution NMI/ARI. Missing Leiden dependencies are marked N/A. No clustering labels are used as true cell types.

## LISI and neighborhood batch testing

LISI follows the original LISI implementation's probability weighting: for the 3*perplexity nearest other cells, `p_ij ∝ exp(-beta_i*d_ij)`, with beta fitted to entropy `log(perplexity)`. Default perplexity=30, entropy tolerance=1e-5, maximum 50 search steps. A probability-invariant distance shift prevents numerical underflow. For each category c, `p_ic=sum_j p_ij*1(label_j=c)`; `LISI_i=1/sum_c p_ic^2`. Report mean and median. Modality iLISI ranges from 1 to 2; higher indicates more mixing. Cell-type cLISI has minimum 1; smaller means less mixing of reference cell types. These are coordinate-based, Gaussian-distance-weighted LISI values, not scIB's graph-geodesic LISI or an unweighted inverse-Simpson proxy. No independent batch iLISI is available.

Canonical R kBET/scIB is unavailable in the reused environment and is recorded as N/A. A separately named `kbet_modality_fixed_k_rejection` implements the core Pearson neighborhood test as an explicitly documented variant: within each reference cell type, all cell anchors use k=50 nearest other cells; observed modality counts are compared with expected counts `k*n_modality/n_type`. Pearson statistic is `sum_c (O_c-E_c)^2/E_c`; chi-square df=`n_categories-1`; rejection threshold alpha=.05. Report the macro mean rejection fraction across eligible cell types (lower indicates closer agreement with expected mixing), and eligible cell fraction. Types with k<10, one modality, or expected counts<5 are excluded. There is no canonical R implementation's repeated anchor subsampling, heuristic k selection, or outsider-frequency adaptation, and this output must not be presented as identical to canonical kBET. Neighborhood tests are dependent; rejection fraction is a descriptive diagnostic and does not establish a significant difference between conditions.

Primary references: [Harmony/LISI paper](https://doi.org/10.1038/s41592-019-0619-0), [LISI implementation](https://github.com/immunogenomics/LISI), [kBET paper](https://pubmed.ncbi.nlm.nih.gov/30573817/), [kBET implementation](https://github.com/theislab/kBET).

## Within-modality conservation

If existing `rna_unirep.h5ad` and `atac_unirep.h5ad` are present, they are aligned by cell ID and checked. Otherwise `--references derive` generates evaluation references once under the reporting directory, using the existing GLUE evaluation recipe: RNA normalize-total, 2,000 preselected HVGs, log1p, scale clipped at 10, PCA 50 components; ATAC GLUE TF-IDF/log-normalized randomized-SVD LSI 50 components, all peaks, n_iter=15. The evaluation seed is explicitly supplied to PCA/SVD. References are not saved training embeddings (training used alt_dim=100). Reference files are never written to the raw input directory.

GLUE neighbor conservation is the mean within-assay Jaccard overlap of pre/post integration neighbor sets; k=`round(.01*n_combined)`, capped by assay cell count. References are generated once and shared across all model seeds. If reference derivation is disabled and references are absent, conservation is N/A. Saved references and their hashes are recorded in `reference_provenance.json`.

## Graph topology

The training implementation `graph_perturbation.py` reconstructs graphs deterministically. Every saved perturbation metadata field must equal the reconstructed value. Biological edge units are reciprocal gene-peak pairs (one forward and one reverse edge); node self-loops are separate. Report node count, total directed edge count, loop count, biological pair count, pair-count fraction, overlap/original-count, overlap percentage, pair Jaccard, and perturbation strength `1-overlap/original-count`.

Non-loop out-degree (one per biological relation incident to a node in the reciprocal directed graph) is compared nodewise: exact preservation fraction, mean absolute change, distribution KS statistic (no p-value), mean, sample SD, quantiles, maximum and isolated-node fraction. Randomization preserves degree and pair count but not endpoint identity; 100% pair count does not mean 100% original pairs retained. Its carried genomic `dist` attributes are provenance and are not interpreted as valid new genomic distances. One graph seed per condition means degree and graph counts repeat identically across model seeds; they are not independently replicated graphs.

## Gates

Saved YAML supplies mean, min, max, initial mean, trainable count, maximum absolute logit change. Trusted project `final.dill` files supply individual gates via `get_graph_gates()` on CPU. Evaluation checks edge topology against the reconstructed graph, fixed self-loop gates=1, finite non-loop gates within [0,1], count and mean against diagnostics. Without individual model gates, distribution metrics are N/A, not reconstructed from aggregate summaries.

Only directed non-loop gates enter mean/median, sample SD, q01/q05/q25/q75/q95/q99, fractions below .1/.5 and at least .9/.95, sum of gates (soft directed edge mass), and reciprocal mean absolute difference. Initial-to-final mean change is also recorded. Thresholds are descriptive choices, not learned hard pruning decisions. Sample SD across gates describes that distribution, not uncertainty across biological replicates. Reciprocal gates are dependent. Gate/integration correlations use Spearman rho across runs without inferential p-values and are confounded by graph condition.

## Summaries, ranks and uncertainty

All available metrics are computed per model seed. Summary mean and sample SD use ddof=1 over available model seeds; n is always recorded. A singleton smoke run has SD N/A. Baseline tables report condition-minus-original mean, same-model-seed matched difference mean and sample SD. Percent change `100*(condition_mean-original_mean)/original_mean` is reported only for nonnegative-scale metrics with positive baseline; signed silhouettes, ARI and already-centered change metrics are N/A. Percent change in a loss such as FOSCTTM is not percent improvement; consult direction. Rankings are metric-specific and respect higher/lower directions; counts/parameters are not ranked.

Retention Spearman trends use five condition means, exclude randomization and are descriptive only. No significance test, confidence interval or causal claim is drawn from three model seeds. Cells, gates, reciprocal directions, nested graph subsets, and repeated model seeds on the same graph are not independent experimental units. Additional graph seeds/datasets are needed for general claims.

## Execution and provenance

Full evaluation requires a Slurm allocation by default. The CPU-only launcher reuses the reference GLUE conda environment, disables CUDA, fixes numeric thread counts and writes scheduler logs outside training runs. Distances are chunked, neighbor queries use sklearn working-memory bounds, and Scanpy uses a sparse neighbor graph. Heavy computation and reference preprocessing occur in the batch job.

Each run is checkpointed atomically after successful evaluation. Checkpoint fingerprints incorporate evaluation parameters, environment versions, code hashes, source input size/mtime, pairing evidence, manifest hash, and SHA256 hashes of every embedding, metadata file, and saved model. Changed configurations require a fresh output directory. Generated derived references are cached under that fixed configuration. REPORT.md, REPORT.pdf, six required CSVs and figures are generated only after selected runs finish. `--mode report` regenerates presentation artifacts from existing tables; it does not recompute metrics. The smoke report is conspicuously marked as a sample test and is never presented as the full evaluation.
