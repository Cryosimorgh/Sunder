# P10 — General-purpose headless simulation core

**Implementation:** branch `p10-headless-world-api-20261031`.
**Gate:** NO-GO until Windows/D3D12 native acceptance is demonstrated. This
application-facing adapter uses the already merged GPU 3D sphere solver. It does
not replace the planar billiards compatibility pipeline. PR #6 P9 remains
INCOMPLETE for bitwise replay; the P8b rail fix is already MERGED.

## API and limits

Public module `sunder_world.py` exports `WorldConfig`, `Body`, `Handle`, `World`,
`Snapshot`, `TickResult`, `WorldError`, `replay_record` and
`compare_replays`. World methods include create/remove/update bodies,
force/clear-force/impulse, fixed-step/async-step/poll, acquire/release snapshot,
grow capacity, record commands, and close. Worlds are independent native
contexts; handles are generation-safe, carry an opaque world identity and are not interchangeable.

Supported units: metre, kilogram, second, Newton, Newton-second. Bounds are
**authoring bounds**, not collision walls. The configured native model handles
3D sphere/sphere contacts with mass, solid-sphere inertia, restitution, Coulomb
friction, velocity, angular velocity, and static/dynamic policies. Force
persists until explicitly cleared. Impulse applies once at the next boundary.
The existing kernel supports sleep counters and motion-driven wake; the wrapper
does not invent a separate CPU physics solver.

Configuration explicitly defines capacity, contact budget, iterations, fixed
dt, gravity, spatial cell size, authoring bounds, shader directory, debug mode,
and deadline. Empty worlds are supported. Capacity grows only at an idle,
lease-free boundary and reuses the native storage/admission infrastructure
via a new context whose native tick clock is restored. That operation temporarily
requires two allocations and may fail admission without altering the old world.

Unused GPU capacity is represented as physically inert static proxies outside
the authoring domain. Public slots remain stable through removal and growth; cross-world aliasing is rejected;
there is **no GPU dense compaction or sparse-slot optimisation**. GPU compute
and memory scale with capacity, not just authored active bodies. No claim of a
million-body arbitrary connected graph or general-purpose GPU-sparse scaling
is made.

## Publication, async, and leases

Commands are validated and ordered in a host candidate. A structural/input edit
requires an explicit accepted-state readback. New native
`ph3_stage`/`ph3_drop_stage` operations upload this candidate into an independent
GPU source buffer; the accepted source remains untouched. The existing
prepare → hash → contact → solve/gather → integrate → validate → publish
pipeline then checks all existing numerical, guard, KKT and contact conditions.
Only a successful fence-complete publication advances world tick/epoch and its
handle map. A rejection discards candidate state and preserves the previous
accepted snapshot. CPU commands never bypass GPU validation.

`step_async` uses a single serial worker around the existing synchronous native
D3D12 call, with `poll` for completion; it does not add another GPU scheduler.
Calls to mutate during an in-flight tick return backpressure. Ordinary ticks
leave full physics state GPU resident. On-demand `acquire` performs a full
readback, produces an immutable CPU copy, and acquires an existing native
snapshot lease. A held current-generation lease may block an edit readback unless the accepted-state immutable CPU cache already exists. Release leases explicitly; destruction refuses outstanding leases.
Native GPU consumers continue to use `ph3_track` with a completion fence.

Errors are distinguishable: invalid configuration/command, stale handle,
capacity, out-of-bounds, exhausted generation, host backpressure, rejected
GPU candidate and device/submission failure. GPU rejection error bits are
retained; no tolerance is relaxed.

## Replay

`record()` contains the initial configuration, ordered commands per attempted
tick, status/tick IDs and source, binary, build and adapter provenance.
`replay_record` creates a fresh native world; `compare_replays` compares
corresponding accepted numerical states and reports the first divergent
frame, body handle, field and absolute error with explicit tolerances.
Two independent native runs must pass their own physics validation.
Exact bitwise/cross-device replay remains **UNSUPPORTED**.

## Reproduce on Windows x64 / D3D12

~~~powershell
python build_physics3.py
python -m unittest test_sunder_world -q
python headless_demo.py --capacity 1 --bodies 0 --steps 4 --replay
python headless_demo.py --capacity 16 --bodies 16 --steps 8 --replay
python headless_demo.py --capacity 1024 --bodies 1024 --steps 8 --replay
python run_world_sweep.py --full
~~~

The demo authors and spawns its own scenes without fixture IDs, drives full
GPU contacts, uses force/impulse, removes and reuses a handle, inspects accepted
state, and emits structured JSON + command recording. The full sweep runs the
mock-only CPU lifecycle tests, native 3D numerical CPU-oracle/negative cases,
legacy pool/rail suite, and existing 10K/100K/1M stress runs. Stress consists
of separated moving colliding pairs and is **not** a dense authored scene.

Each native qualification attempt writes immutable evidence under `evidence/p10/world-sweep/runs/<UTC>-<id>/` with `consolidated.json` and logs. The first top-level `evidence/p10/world-sweep/consolidated.json` is retained unchanged; `run-index.jsonl` locates every attempt.
It separates accepted/rejected counts, GPU and host p50/p95/p99/worst, configured and fixed-step deadline
deadlines, memory, and failure causes. CPU-oracle/readback work is reported
separately, not included as production-path throughput. Three-sample historical
P10 stress measurements are not sustained tail-latency qualification.

## Exclusions and decision

No new 3D shape types, terrain, joints, generic ECS, viewer, physical world-bound
planes, GPU-side sparse compaction, native GPU nonblocking polling, or
large-island optimisation. The planar pipeline and its original constraints are
unchanged. The test double in `test_sunder_world.py` checks host transaction
logic only; it is **not** a physics oracle.

A full qualification command was attempted in Windows GitHub Actions at source 510192f (run 41230865897). Host tests and compile PASS, but D3D12 context creation fails on Microsoft Hyper-V Video in the first empty-world scene; remaining native tests were NOT RUN. See [the preserved attempted-run provenance](P10_NATIVE_ATTEMPT_20261031.json) and its original Actions ZIP.
The branch must remain **NO-GO / unmerged** until applicable native tests run
and pass with retained evidence. G5 remains deferred, GPU-02 unverified, formal
G6 and production release not qualified.
