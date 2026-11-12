# Resume GATED tuning

Current point: Stage A array `54050745` is submitted. Monitor every array task
with `squeue -j 54050745` and `sacct -j 54050745 -X` until every required task
is `COMPLETED` with `0:0`. Inspect failures and retry only eligible failed tasks
once. Task 9 reuses the matched model and creates only a provenance pointer.

The latest Fir estimate was `2026-08-12T02:32:31`; all 15 tasks remained
pending due priority/unavailable requested nodes. This is not a failed job and
does not justify a retry or resource-profile change.
