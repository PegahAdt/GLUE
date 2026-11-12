# Before GitHub publication

Proposed repository name: **glue-graph-robustness**. Publish the integration branch as a research release candidate first; do not change main or the default branch as part of this step.

Remaining review items: manuscript-to-figure correspondence and unpublished-work scope; visibility and intended destination; disclosure of original cluster/account/user paths and design cell/edge identifiers; third-party notices and annotation access; external artifact availability; per-run environment/source gaps; frozen portability and incomplete evaluation coverage. These are not resolved by static checks. No fresh GPU reproduction is claimed.

The integration includes only source, designs, compact preserved metrics and provenance. Large datasets, checkpoints, embeddings, generated logs and thesis PDFs remain external. A Git push does not back up untracked active experiments or the locally modified legacy environment recipe.

The existing origin is the researcher's GLUE repository and upstream is Gao Lab GLUE; remotes were not changed. After destination/privacy review, the following normal push targets only the candidate branch and sends no tags. These commands are instructions, not actions already performed:

```bash
git -C /path/to/release-worktree remote get-url --push origin
git -C /path/to/release-worktree ls-remote --heads origin refs/heads/integration/thesis-release-candidate
git -C /path/to/release-worktree push --dry-run --no-follow-tags origin refs/heads/integration/thesis-release-candidate:refs/heads/integration/thesis-release-candidate
git -C /path/to/release-worktree push --no-follow-tags origin refs/heads/integration/thesis-release-candidate:refs/heads/integration/thesis-release-candidate
```

For a new GitHub destination, create/review it separately, then substitute its reviewed URL for origin or authorize adding a new remote. Do not push to the Gao Lab upstream, use `--mirror`/`--all`, overwrite existing history, or merge into main without explicit approval.
