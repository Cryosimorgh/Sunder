# Next-step Codex prompt — P10 native qualification

On the dedicated branch `p10-headless-world-api-20261031` of
`Cryosimorgh/Sunder`, complete the P10 general-purpose headless world API
qualification. First use `git status`, `rg` and targeted reads of `physics3.c`,
`sunder_world.py`, new tests and `docs/P10_WORLD_API.md`. Do not overwrite
uncommitted work. Review the transactional candidate source, leases, rollback,
tick continuity across growth, handle generations, replay fidelity and
backpressure/device-error classification. Fix actual defects without relaxing
KKT/energy/contact/tolerances or editing shader physics. On Windows/D3D12 run
`python run_world_sweep.py --full` once, preserving all JSON/log/build hashes;
include empty/16/1K authored scenes, native stage rejection, two independent
numerical replays, old pool/rail regression and genuine contact-bearing
10K/100K/1M separated-pair stress where supported. Record p50/p95/p99/worst,
deadlines and committed memory; separate production path from CPU oracle.
Reconcile any new regressions and retest. Update
`docs/ENGINE_ARCHITECTURE.md` and `docs/P10_WORLD_EVIDENCE.json` in the same
commit. Review the PR and merge only when applicable physics and safety gates
genuinely PASS; otherwise retain a marked NO-GO PR with exact blockers.
Do not expand scope to terrain, joints, ECS or display.
