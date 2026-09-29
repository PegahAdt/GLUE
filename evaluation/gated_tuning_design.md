# Bounded GATED tuning design

The search keeps the matched GLUE settings fixed (`lr=0.002`, `lam_graph=0.02`,
`lam_align=0.05`, `dim=50`, `alt_dim=100`, two 256-unit hidden layers,
`dropout=0.2`, 10 negative samples, batch size 128, model seed 0) while first
tuning only `gate_init` and `lam_keep` on the prepared size-2000, subsample-seed-0
benchmark subset.

`GatedGraphEncoder` assigns one sigmoid logit to every directed non-self edge;
self-loops remain fixed at one. The retain penalty is the unnormalised sum

`L_keep = sum_e (1 - sigmoid(logit_e))^2`.

The authoritative matched diagnostics report 26,986 trainable gates. Therefore
the exact initial raw penalty is `26986 * (1-gate_init)^2`: 6746.5, 1686.625,
269.86, 67.465, and 2.6986 for initial gates 0.50, 0.75, 0.90, 0.95, and 0.99.
Since this term is added directly to the VAE objective, ordinary regularisation
weights would be indefensible. Stage A uses `lam_keep={0,1e-5,1e-4}`, whose
initial weighted contributions span 0--0.67465 over the grid, and five gate
initialisations. This is 15 configurations, but the exact matched baseline
(`0.95,0`) is reused, leaving at most 14 new GPU jobs.

The feature-consistency implementation correlates within-feature cosine
similarities between a subsample embedding and a full-data feature embedding.
Because gate hyperparameters can change that learned feature geometry, the
scientifically meaningful reference is a full-data model with the same
`gate_init`, `lam_keep`, and `lam_graph`. Feature consistency is consequently
marked deferred in early screening and computed for finalists using one
configuration-matched full reference per finalist.

All training and nontrivial metrics run through Slurm. Training jobs use one
H100, 8 CPUs, 192 GB RAM, and 48 hours. Every runner exports the repository as
`PYTHONPATH`, disables user-site packages, and verifies that `scglue` resolves
inside this checkout before accessing data.
