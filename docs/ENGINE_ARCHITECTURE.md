# Sunder — Technical Architecture and Development Record

**Project:** [Cryosimorgh/Sunder](https://github.com/Cryosimorgh/Sunder)  
**Record date:** 2026-11-02
**Document type:** Living engineering record  
**Style:** Clear technical English, based on ASD-STE100 principles without strict controlled-language limits  
**Status:** G7 native Win32/D3D12 3D application IMPLEMENTED; bounded local 512/1K native evidence PASS. PR #9 stays DRAFT / merge NO-GO pending final acceptance. Original dense radial stress and full-scale qualification remain unqualified. **P10 native 3D foundation: GO within the historical bounded tested envelope. P10 general-purpose headless world API: BOUNDED NATIVE CORRECTNESS GO at ed618f9; final-head sweep and CI required before merge.** G5 is **DEFERRED / NOT QUALIFIED**. G6 and production release remain **NOT QUALIFIED**. P9's bitwise replay guarantee remains unresolved and does not block numerically validated 3D development. P4 remains an explicit rendering option; matching-tick rendering remains the default for the planar viewer.

> **Update rule:** Update this document in the same change that closes, rejects, or reopens a development breakpoint. Keep prior results and their limitations. Do not turn a local experiment into a released feature by changing its status here.

## 1. Purpose and scope

The project tests a **GPU-first physics architecture** for many moving entities and contacts. It uses native Zig and C on Windows, Direct3D 12 for GPU execution, and HLSL compute shaders for simulation. The original **two-dimensional disk** and billiards models remain compatibility modules. P10 adds genuine headless **3D sphere/sphere and sphere/plane rigid-body dynamics**. This is a bounded foundation, not a general engine with arbitrary collision shapes.

The central design aim is to keep the simulation state and most calculations on the GPU. The CPU configures work, submits commands, processes bounded results, and controls resource lifetime. It should not move every entity to system memory after each tick.

This repository is an **independent experiment**. It does not depend on Unity or GGG. Integration with another application is a later design decision, not a completed feature.

### Evidence boundaries

There are two different development baselines:

- [`main`](https://github.com/Cryosimorgh/Sunder/tree/main) now includes merged P8b pool precision, P9 incomplete evidence (PR #6), and the bounded native 3D P10 foundation. The earlier G4-only main statement was historical and is no longer accurate; G5 optimization research is still not qualified.
- [`billiards-playable-requalification-20261018`](https://github.com/Cryosimorgh/GPU-physics-engine/tree/billiards-playable-requalification-20261018) stores the later playable billiards, headless test workflow, and revised shaders. Its test and README claims apply to that branch.

G5 results in this record come from **user-supplied local handoff results**, not from a G5 release on `main`. The latest uploaded `results.json` describes a quick, two-sample, cold, one-tick sweep. It explicitly marks `qualification: false`.

Use these labels throughout the document:

| Label | Meaning |
|---|---|
| **Implemented** | Code exists in a named repository revision. |
| **Measured** | Recorded execution data supports the stated workload and hardware. |
| **Conditionally accepted** | The scoped tests pass, but at least one exit condition is open. |
| **Experimental** | A local or branch-specific change needs broader evidence. |
| **Planned** | A design target. No implementation claim. |

### G7 reference motion and solver breakpoint (2026-11-02)

**Current default:** native sphere rain into a rendered sloped trough, based on
actual inspection of the user's video. Five real Physics3 planes define floor
z=-8, .75 slopes and end walls +/-16; the front is a visual cutaway. Smooth
spheres (.92 restitution, zero friction) fall under -19.62 gravity. The larger
container is a separately qualified demo envelope; narrower/frictional pile
failures are preserved, not promoted. Cube/belts remain explicit scene presets.

**Solver contract change:** small connected graphs use a GPU-built active-edge
coloring and projected Gauss-Seidel with accepted-only sparse warm starts.
Color members share no body. Inactive constraints re-enter the active set when
needed; all constraints face the unchanged final KKT/penetration validator.
There are 17 compute kernels, an 8-byte predication resource, grid coloring/list
workspace and a bounded cache in free-state scratch. The Jacobi path remains for
larger/uncolorable graphs. Numerical replay remains distinct from bitwise replay.

`ph3_stage_append` preserves existing accepted rows on GPU while admitting new
slots transactionally. Failure rolls back all admissions. The lease and result
ABIs are unchanged. Mandatory 256-byte metadata synchronization is part of the
production solver cost, not optional diagnostic cost. GPU elapsed timestamps
include host gaps between command packets; isolated kernel busy time is not
reported. Optional verification readbacks are outside the production display path.

**Render/pacing:** two accepted GPU snapshots supply render-only interpolation;
new births and epochs bypass history. No candidate/rejected state feeds graphics.
The 1/128-s clock is unchanged. High-resolution scheduling and requested/achieved
rate reporting replace the ineffective saturated speed control. Native pacing
measures approximately 32/64/128/256 TPS at .25/.5/1/2x on the pacing case. Manual
UI operation confirms changed native rate and truthful throughput-limit reporting.
Present counters and timestamp aggregation remain bounded through minimization.

**Local evidence:** RTX 4070 Ti SUPER; 512 and 1K reference cases each accept
3200 ticks, no rejection. The 1K mean GPU timeline is approximately 4.87 ms. Legacy
512/1K cube/belt cases pass 768 ticks with actual geometric cross-belt contacts.
The formerly rejected radial activation now passes tick 9; sustained radial
compression remains unqualified. Six native G7 tests, 28 CPU contracts, eight
P10 oracle groups and eight native-world groups pass. Native images confirm
falling, bouncing and accumulation; a full 1K/1080p test renders 600 frames in
4.997 s after warmup, with minimum/maximum population 1000.
See [G7 usage/evidence](G7_DENSE_WORKLOADS.md) and the machine-readable
`G7_REFERENCE_MOTION_EVIDENCE.json`. Earlier failures and per-case data remain in
one focused ZIP. No final acceptance predicate or tolerance was weakened.

**Gate boundary:** bounded local demo PASS; PR #9 remains DRAFT / merge NO-GO
pending independent review. Dense frictional piles, edited seeds/settings, big-world
performance, physical device loss and a full previous-gate sweep are NOT QUALIFIED.
This solver change does not inherit the old binary's complete hardware campaign.
G0-G4 retain their historical scope; G5 deferred, G6 unqualified and P9 unresolved.

### Historical first native graphical application breakpoint (2026-11-02)

**2026-11-02 direct-launch correction:** Runtime assets and evidence resolve from
`zig-out/bin/SunderG7.exe` to the project root, independently of the invoking
working directory. Missing shader assets receive a specific build instruction.
The reported 600-frame benchmark failure from `zig-out/bin` reproduced before
the fix (exit 1) and passes afterward (600 frames at 1920x1080, exit 0). Five
native tests pass, including unrelated-directory launch, lifecycle, rejection
rollback and controlled API removal. Physics policy and qualification are unchanged.

Primary entry: `LAUNCH_G7_CAPABILITIES_DEMO.cmd`; the old demo CMD redirects
there. `g7_demo.cpp`, `g7_scene.h`, and `g7_render.hlsl` replace the primary
Tkinter display with Win32/D3D12 perspective sphere impostors, analytic surface
depth, one GPU instanced draw and the pinned ImGui backends. A physics worker
executes fixed 1/128-s native ticks independently of rendering. CPU scene
code authors initial conditions only: opposing waves in a 3D sphere cube and
two separated volumetric toroidal clouds with counterrotation and closing speeds.

**Ownership:** a narrow internal native device/resource bridge validates the
existing accepted-state lease. An SRW lock serializes Physics3 access; the
render thread tries it without waiting for a tick. It copies accepted data
GPU-to-GPU into its own snapshot, tracks the DIRECT-queue fence before submission
and releases afterward. Buffer COMMON promotion/decay preserves producer resource
state. Snapshot/allocator reuse waits for the frame fence. Busy physics renders
the previous accepted GPU snapshot. No per-frame CPU body readback or collision
interpolation occurs. Fixed capacity is 1,000 native slots, with static parked
unused slots excluded from admissions/drawing. Scene epochs separate handle
identities. Rejected ticks cannot advance admissions. Unfenced work is quarantined.

**Physics boundary:** additive diagnostic atomics record normal/tangent residual
ratios and penetration witnesses. Counts can be partial after fail-closed exit.
No solver equation, acceptance predicate or tolerance was weakened. The original
512-body dense radial cube accepts fill tick 8 then rejects flags 12: degree 32,
6,220 constraints, KKT and penetration witnesses (0.003741 units). Slower radial
compression also fails later. That stress case remains unsupported. The separate
native demo uses cube speed 0.7 / belt closing 0.6, 1.0 cell, 12,000 contacts and
512 application iterations. Engine defaults are unchanged. Late 128-iteration
rejections are retained as evidence, not silently discarded.

**Measured locally:** RTX 4070 Ti SUPER, driver 32.0.16.1088. Four 512/1K cube/belt
cases each accept 768 ticks; native raw gap<=0 cross-belt contacts and positive
impulses are observed. Physics allocation is 4,653,056 bytes. A separate 1K 1080p
run renders 600 frames in 10.210 s (58.77 FPS), mean rendering GPU time 60.8 us
including the accepted-state copy. Sampled native physics averages about 49-56 ms;
no 128-TPS or OS displayed-frame/latency claim. Commands, final repetition and
focused handoff evidence are described in [G7 documentation](G7_DENSE_WORKLOADS.md).

**Checks:** 28 CPU contracts; eight P10 native oracle groups; eight native-world
groups; G7 byte-for-byte rollback, delayed/stale lease, actual window lifecycle
and controlled API device-removal tests pass. Visual inspection confirms shaded
sphere motion. Physical adapter removal, long leak campaigns, edited settings and
full-scale qualification remain NOT RUN. Final visual acceptance and independent
final-head review remain open; **PR #9 stays draft / merge NO-GO**. Historical
G0-G4 scope, G5 deferred, G6 not qualified and P9 unresolved are unchanged.

**Next action:** review native captures and bounded hardware evidence; qualify
longer sessions/edited controls; improve solver scheduling without weaker
validation. Do not promote the original radial stress or larger populations.

### Historical G7 benchmark implementation breakpoint — NOT QUALIFIED (2026-11-02)

**Branch:** `g7-dense-dynamic-collision-workloads-20261102`, based on merged
P10 main `8a5385b11ef108be7e5e530a12ce133152ea0896`.
The branch adds `g7_scenarios.py`, `run_g7.py`,
`run_g7_windows.py`, `RUN_G7_WINDOWS.cmd`,
`test_g7_scenarios.py`, `.github/workflows/g7-cpu-contracts.yml`,
and [G7 workload instructions](G7_DENSE_WORKLOADS.md). A small
`sunder_world.py` adapter change exposes optional native `ph3_contacts`
readback (128-byte contact records) plus measured candidate staging and
native host submission/completion, candidate count and maximum degree per
tick. The D3D12 physics kernel, configured P10 iterations and acceptance
thresholds, and old planar physics source are **unchanged**.

The cubic spawning volume authors 3D spheres on a seeded nonoverlapping
lattice, fills exactly the configured capacity in accepted per-tick batches
as active temporary static spheres, then changes all bodies to dynamic on the
tick after full acceptance. This holds under nonzero gravity and enables
inward, swirl or funnel velocity fields. The second scene authors two disjoint
seeded 3D toroidal clouds that counter-rotate and close along opposite x
directions. No cube collider, CPU contact solver, N-body gravity, general
GPU renderer or precomputed contact pairs have been introduced.
Sparse P10 slots still use inert placeholders. CPU scene authorship and
structural edits remain separate from GPU simulation timing.

Instrumented native contact readbacks distinguish overlapping/impulsive
contacts from speculative constraints. A positive-gap normal impulse never
counts as proved cross-belt geometric overlap. The sampled graph gives connected
components, largest island, degree, cross-belt edges and contact churn.
It is a **diagnostic path**, not a normal production tick, and contact
sampling cadence can miss the absolute peak. Preset-dependent explicit
contact budgets are used to avoid pretending sparse separated-pair memory
budgets qualify dense contact topology. Native per-tick counters,
seven actual GPU-stage timing distributions, GPU/host percentiles,
separate diagnostic readback and host graph times, fixed-step misses,
driver/adapter, recorded hashes, active/attempted body counts, rejected
creation counts and error causes are emitted. Sample-inferred pre-impact,
first contact, peak and post-impact phases use distinct CSV/JSON records. The Windows
runner attempts all required 1K/10K/100K workloads with independent native
worlds and existing P10 full gates; it creates a unique, checksum-inventoried
failure-inclusive ZIP. Above 100K requires explicit opt-in and memory
admission. CPU scene tests and CI do **not** validate the D3D12 physics.

**Current evidence:** The user reported one G7 Windows full-suite attempt:
`build_physics3`, G7 CPU scene contracts and P10 CPU contracts PASS;
`g7_native_both` and `p10_native_full` FAIL. The original logs have
not yet been supplied or audited. The first ZIP package attempt also failed
because archive keys used Windows path separators, so no verified handoff
was produced. The following focused branch correction uses explicit POSIX
archive members, streamed SHA-256 verification and a repackage-only option
(`python run_g7_windows.py --package-existing latest`). A cross-platform
synthetic failing-run archive regression passes in CPU CI. No new native
hardware qualification was executed by this author. No measured G7 performance or
large-island GO is claimed, no 1M arbitrary-connected qualification, and
no P9 bitwise, G5 or production-release promotion. Keep the PR draft until
an exact tested SHA, full native accepted runs, genuine cross-belt
overlaps/impulses, dense multi-body islands, unchanged P10 physical gates,
full required-vs-executed matrix and independent reviewer audit are present.

**Visual demo follow-up (2026-11-02):** Implemented `g7_visual_demo.py`
and `LAUNCH_G7_DEMO.cmd` as a real interactive display of native
accepted GPU sphere positions. User controls switch between the cubic
spawning volume and the two toroidal belts, orbit/zoom, pause/play, density,
body capacity and batch size. On every displayed frame, `World.acquire()`
performs an explicit GPU readback and Tkinter paints projected 3D spheres.
This is **GUI demonstration evidence**, not an efficient GPU renderer,
and its host wall/readback times must not be mixed with headless hot-loop
latency. Native sphere contacts are still computed by P10 D3D12, never by a
new CPU solver. GUI acceptance on user's Windows adapter is pending.

**2026-11-02 change log:** Created G7 CPU-authoring and native benchmark
evidence interface on the dedicated branch; hardened temporary static fill
against gravitational drift; separated positive-gap impulses from geometric
cross-belt impact evidence; instrumented all seven native GPU phases; retained
full P10 native raw evidence in the unique G7 handoff. Preserved old
physics/kernel code and thresholds. Open risks: 100K dense contact budget/admission,
P10 speed-envelope rejections, biased diagnostic sampling, GPU budget
limits, and unexecuted hardware qualification. Decision: **G7 NO-GO**.

### Application-facing headless world API — P10 bounded native evidence GO (2026-11-02)

**Current audit (2026-11-02):** User hardware run `20261031T195427Z-3f1028cd` passes all nine full-sweep gates at `ed618f9bf7c80bd78f8d73d57f38f7791d3f6dfe`, Windows 11 x64, RTX 4070 Ti SUPER, driver `32.0.16.1088`. ZIP CRC, all 135 checksums, 14 sweep-source and 14 native-build source hashes verify. Eight native world cases, eight native oracle groups, all eight legacy dev-test cases and 10K/100K/1M separated-pair stress PASS. Expected native-world rejections: leased-slot backpressure and injected validation flag 16; recovery PASS. No physics defect or tolerance change indicated. The runner verdict defect found below is corrected. Raw original files: `evidence/p10/qualification-20261102/original/`. [Detailed audit](P10_NATIVE_AUDIT_20261102.json). The hosted failure and preparation-only statements below are historical, superseded by this hardware evidence.

Authored 16/1024 GPU p50/p95/p99/worst are 1151.75/1152.5/1152.5/1152.5 and 3004/3024.6/3030.92/3032.5 microseconds. Host worst is 2344.9/4441.2 microseconds, zero reported deadline misses. Stress GPU medians: 1852.25/7323.25/60727 microseconds; tracked bytes: 16,187,392/155,779,072/1,552,875,520. Three degree-1 samples per size; all three 1M samples exceed the 7.8125 ms step. No sustained, real-time or arbitrary-topology claim. Stress host per-tick timing and allocation-event counts unavailable; CPU thread zeros reflect coarse accounting. Archive omits DLL/DXIL bytes, so output hashes are recorded, not recomputed from it.

**Verified runner correction:** An injected failure in the final `native-stress` gate reproduced exit 0 and `qualified=true` because the failed gate exhausted `unexecuted` and the loop then promoted the verdict to GO. Return immediately on any failed gate, retaining NO-GO in the finalizer. Regression tests cover each of the nine gate positions and the all-pass path; all 21 host/packaging/verdict tests pass. The new regression runs in full-sweep CPU tests and CI. This does not invalidate the uploaded run: its original stress JSON and logs independently pass. No kernel, API, tolerance or solver-budget change. Intermediate reviewer full run `20261102T060628Z-5ad8b2f7` passes all nine gates on `032cffc`; a new exact full sweep must qualify the corrected final commit.

**Integration condition:** Run exact `python run_world_sweep.py --full` on the final documentation/evidence commit, attach immutable results and SHA to PR #8, check CI and compare live PR head before merge. Bounded P10 correctness only. P9 bitwise stays INCOMPLETE; G5 DEFERRED, GPU-02 UNVERIFIED, formal G6 and production release NOT QUALIFIED.

**Implementation proposal:** [P10_WORLD_API.md](P10_WORLD_API.md) describes
`sunder_world.py`, `headless_demo.py`, `run_world_sweep.py`, the new native
`ph3_stage`/`ph3_drop_stage` candidate source and host error classifier, and
`test_sunder_world.py`. The new layer wraps existing D3D12 3D sphere
simulation; it does not alter the 2D physics kernel or weaken its gates.
A candidate GPU source is kept separate from accepted snapshot slots until the
GPU validation/publish fence succeeds. The host generation map is committed
only alongside the accepted native tick. Fixed-step clock continuity is
explicitly restored on capacity growth.

Worlds author spheres and expose typed MKS units, bounded capacities, stable
generation handles, per-body properties, forces/impulses, fixed-step/async
completion, immutable acquired snapshots, ordered command capture and
numerical replay comparisons. Native GPU state remains resident on ordinary
ticks. Input edits and explicit CPU state inspection require full-state
readbacks. Inert GPU proxies retain unused stable slots; there is no claim of
efficient sparse-body compaction. An adapter's authoring bounds are not physical
wall contacts. Replay requires independently accepted physics within tolerance;
bitwise determinism stays unsupported.

**Native hardware handoff suite (2026-10-31, NOT YET RUN on user machine):**
`RUN_P10_WINDOWS.cmd` invokes the exact existing
`run_world_sweep.py --full` command and creates a per-run SHA-256-inventoried ZIP
using `package_p10_evidence.py`. The consolidated full sweep now includes
`test_native_world.py` as a mandatory D3D12 world-API gate (handle generation,
growth, collisions/friction, force/impulse, sleep/wake, three snapshot leases,
backpressure, rejected candidate rollback and two fresh native replays).
Existing 16/1K authored, GPU CPU-oracle, pool/rail/device and 10K/100K/1M
separated-pair stress remain mandatory. Each run has immutable evidence paths,
driver inventory, source/tool hashes, GPU and host timings, and explicit NOT RUN
statuses after the first failure. [Instructions](P10_RUN_ON_WINDOWS.md).
The prior hosted GPU hardware NO-GO remains valid; merely preparing a suite
does **not** qualify or merge P10. Physical thresholds are unchanged.

**Full-sweep attempt on Windows 2025 hosted runner (2026-10-31, NO-GO):** The exact `python run_world_sweep.py --full` command ran on source commit `510192f` in [Actions run 41230865897](https://github.com/Cryosimorgh/Sunder/actions/runs/41230865897). The 17 host-only unit tests PASS and native Zig/DXC compiles nine shaders and DLL (57.14 s). The first native case, an empty authored world, fails at D3D12 context/admission: the only video adapter is Microsoft Hyper-V Video (driver 10.0.26100.1150). This is an **environment gate**, not verified solver failure or GPU-physics PASS. Fail-fast leaves authored 16/1024, native CPU oracle, leases, numerical replays, legacy pool/rail and 10K/100K/1M stress **NOT RUN**. No new physics timing/driver-performance conclusion is permitted. Original immutable per-run evidence is [Actions artifact 13053607373](https://github.com/Cryosimorgh/Sunder/actions/runs/41230865897/artifacts/13053607373), SHA-256 `874cae88d8970b14457317ade4836f58afca7818e36f72a58c2d1a26b8e9a211`. Persistent provenance summary: [P10_NATIVE_ATTEMPT_20261031.json](P10_NATIVE_ATTEMPT_20261031.json). PR #8 remains draft/unmerged; formal G6 and production release remain unqualified.

**Evidence boundary:** The follow-up native qualification review added fail-closed staging cleanup, early-discard error quarantine, transactional resize host-map preparation, a closing gate for asynchronous teardown, full 3D replay numerical fields and run-isolated evidence (`run_world_sweep.py --full`, per-run immutable JSON/logs, source hashes, GPU driver inventory). An injected async-close test initially failed because the test required BACKPRESSURE even after shutdown had started and CLOSED was correct; the test assertion was repaired without changing physical gates. The extended host test suite and native qualification must be evaluated against the final tested SHA before merge. No fresh D3D12 physics measurements are available. Host contract GitHub Actions PASS (10 Python mocked-backend unit tests; Linux runner `41229876886`, commit `93ea51d`) and Windows compile-only GitHub Actions PASS (9 original compute shaders + DLL + syntax, run `41229757701`, commit `5069f6c`). These checks do **not** execute D3D12 physics or independently validate the GPU result. The implementation was written through a GitHub
connection in an environment without Windows/D3D12 execution. All new native
and compatibility gates remain **NOT RUN** in this branch until an independent
`python run_world_sweep.py --full` executes on supported hardware and commits
consolidated JSON/log evidence. The Python fake-backend unit suite cannot
qualify physics. Existing [P10_EVIDENCE.json](P10_EVIDENCE.json) pertains only
to the earlier merged native 3D foundation and is not a test result for the new
world adapter. Do not merge this PR without a verified GO. G5 is DEFERRED;
GPU-02 is UNVERIFIED; formal G6 and production release remain NOT QUALIFIED.

## 2. System layout

### P10 native 3D foundation — GO (2026-10-31)

**Plan and source:** [P10_DESIGN.md](P10_DESIGN.md), `physics3.h/.c/.hlsl`,
`physics3-schema.json`, `build_physics3.py`, `test_physics3.py`, `run_p10.py`.
This isolated module reuses the existing D3D12 StorageDevice runtime, admission,
resource claims, barriers, checked fences, timestamp queries and retained native
completion objects. The old planar ABI, solver and acceptance thresholds are
unchanged. Generalizing a public world API follows this foundation, not vice versa.

**3D state:** A 48-word binary32 SoA holds xyz position, velocity, force, torque
and angular velocity; xyzw quaternion; inverse mass, radius and materials; six
independent entries each for body inertia and inverse inertia; sleep count and
slot/generation identity. Dynamic tensors must be symmetric positive definite
and mutual inverses. The input schema documents exact offsets. `invMass=0`
means a static sphere. Planes have an arbitrary unit inward normal and signed
offset. Near-unit imported plane normals are normalized in binary64 together
with their offset. Tests use metres, kilograms and seconds.

**Passes and contacts:** Prepare -> xyz spatial hash -> bounded narrowphase ->
projected contact impulse update -> per-body adjacency gather -> integrate ->
validate -> publish. Solve/gather repeat within a fixed work budget. Hash bucket
collisions are resolved by exact signed cell-coordinate checks. All 27 neighbor
cells are searched. Reachable speculative constraints are formed even if a body
was initially stationary; the tested three-sphere transfer case would otherwise
miss a new collision after an impulse. Source and final speeds must satisfy
`2*radius + 2*speed*dt <= cell_size`; cell coordinates are bounded to magnitude
1,000,000. Violations reject the whole tick. This envelope proves the stencil's
reach; it is not exact swept time-of-impact integration.

Contacts use a binary64 normal impulse and a full xyz tangent impulse projected
onto a circular Coulomb cone. Body orientation transforms inertia tensors for
angular response. Restitution and friction combine by minimum for two spheres;
static planes use the sphere material. A 0.5 m/s impact threshold suppresses
resting restitution. Positive-gap constraints use separation/dt when inactive;
initially imminent impacts may bounce speculatively. Degree-relaxed Jacobi
supports coupled contacts without concurrent body writes. A fixed budget may
reject difficult contact networks; P10 does not resolve G5 convergence debt.

Orientation uses the post-impulse world angular velocity for a quaternion
exponential step. World angular momentum is then transported through the updated
inertia tensor. This preserves angular impulse/torque transfer when orientation
changes; general anisotropic rotation remains a first-order integration scheme.
KKT checks refer to the solved configuration before orientation advection.
Sleep/wake counters are supported; sleeping bodies still receive force/contact
evaluation. This is not a new sleep-culling optimization.

**Publication/lifetime:** Three bounded state buffers provide immutable accepted
snapshots. The previous generation is read-only throughout a tick. GPU validation
checks state finiteness, quaternion norm, normal/tangent projected residuals,
friction bounds, final separation, speed envelope and buffer guards before the
publish pass. Only a successful fence-complete header advances the host accepted
pointer. Overflow, invalid input, injected rejection and nonconvergence publish
zero bodies. Invalid host edits preserve the previous state. Idle tick-boundary
edits require no leases, preserve the global tick and advance generation. The
first accepted dt fixes that context's timestep. Consumers register native GPU
completion before submission; delayed release retains the resource claim. Slot
exhaustion gives bounded backpressure. Calls are owner-thread serialized.

**Independent local Windows verification:** The seven native groups pass xyz
independent/combined motion, force/torque, quaternion Rodrigues checks, arbitrary
normal/offset planes, elastic/inelastic and grazing/oblique impacts, unequal
radii/masses, static spheres, frictional spin and spin-to-translation transfer,
rotated non-diagonal tensors, a six-contact tetrahedral cluster, impulse-induced
third-body contact, resting/sleep/wake, penetration correction, overflow,
nonconvergence, rejected edits/ticks, fixed-clock continuity and snapshot
backpressure. A delayed real copy-queue GPU reader retains an exact prior snapshot
across a later physics tick. That case and ordinary/injected ticks also pass the
D3D12 debug layer with GPU-based validation. The double-precision CPU oracle
independently recomputes geometry, contact completeness, KKT, impulse transfer,
linear/angular momentum, energy bounds and orientation. `evidence/p10/demo.json`
records five actual accepted frames of twelve colliding and rotating spheres.

| Native 3D stress population | Constraints / max degree | Median complete GPU tick, ms | Tracked committed bytes |
|---|---:|---:|---:|
| 10,000 | 5,000 / 1 | 2.2265 | 14,221,312 |
| 100,000 | 50,000 / 1 | 8.0055 | 136,577,024 |
| 1,000,000 | 500,000 / 1 | 67.15825 | 1,360,855,040 |

Each row is three fresh collision-bearing scenes on NVIDIA GeForce RTX 4070 Ti
SUPER, not later contact-free ticks. Spheres form independent frictional pairs
on a separated xyz lattice, with nonzero xyz motion and angular response.
Constraints/body=0.5; every sphere participates. The CPU checks all-body analytic
normal/tangent impulses and spin, momentum/energy/separation, identity/quaternion
data and a pair-isolation certificate. GPU validation remains enabled. Raw JSON
separates seven GPU phases, total GPU time and wall time including initialization,
readback and CPU verification. Three samples establish neither sustained tail
latency nor a real-time operating envelope, and do not represent a million-body
connected graph. No before/after speedup is claimed: there was no prior 3D path.

**Compatibility:** Existing `python dev_test.py full` passes all eight groups in
306.19 s, including 10,598 accepted analytical ticks, two expected rejections,
10,000 exact stationary-rack ticks, command safety, CPU contracts, device tests,
storage and spatial CLIs. Nineteen workflow/rail/P9 Python tests also pass.
No planar C/HLSL/Zig source or threshold is changed. Rebuilt legacy binaries
are local test artifacts, not new committed production outputs.

**Replay and integration:** PR #6 is merged as P9 evidence after its 237-hash
offline verifier and 19 CPU tests passed; its FAIL/INCOMPLETE result is preserved.
This branch starts at main `acf8d3b`. Two native 3D tetrahedral runs pass the
independent physical oracle and happened to match bitwise locally. Equality is
recorded as an observation only. Numerical validity is the P10 requirement;
P9/cross-device/compiler bitwise replay is not claimed or used to block P10.
The historical P9 proposed-next-task text below is superseded by the owner's
2026-10-31 native-3D instruction, not erased.

**Decision:** **GO for the bounded P10 native 3D foundation. NO-GO for production
release or general topology/real-time qualification.** Convex hulls, meshes,
joints, terrain, generalized ECS and a polished public world API are not
implemented. More coupled/dense/sustained workloads and higher-order anisotropic
integration remain future work. G5 stays deferred, GPU-02 stays unverified and
formal G6 stays not qualified. [P10_EVIDENCE.json](P10_EVIDENCE.json) records the
source hashes and summarized runs; the single handoff ZIP carries complete logs,
build provenance, raw timing rows and the accepted-state demonstration.

```text
Inputs / scene / structural commands
             |
             v
      CPU command control
      - resource admission
      - command lists and fences
      - fixed global tick number
             |
             v
       GPU simulation passes
   1. Prepare provisional state
   2. Build spatial search data
   3. Find candidate body contacts
   4. Add wall and contact constraints
   5. Build connected contact islands
   6. Color and solve constraints
   7. Check physics and memory guards
   8. Publish accepted state generation
             |
             +----> GPU rendering of a completed generation
             |
             +----> Bounded diagnostic and timing readback
```

The order is important. Broad-phase search must precede contact solving. Contact graph data must be complete before the solver uses it. A result must pass validation before clients treat it as accepted state.

**Architectural gap:** The G4 `ph_publish` shader writes accepted per-body results back to the original `source` buffer. It is guarded by validation, but it is **not yet a strict full-generation buffer swap**. The intended rule is that `S(t)` remains read-only for the entire tick, and only a validated `S(t+1)` becomes visible. This requirement remains open until source bindings, publication, in-flight ownership, and failure behavior prove it. Do not call strict immutable snapshot isolation complete.

## 3. GPU backend and execution control

**Code:** `api.h`, `runtime.c`, `runtime.h`, `physics.c`, `viewer_runtime.c`.

The backend creates a D3D12 device, queues, resources, command allocators, command lists, query heaps, and fences. HLSL shaders compile into DXIL. The host uses explicit resource states, GPU command ordering, and fence completion to control reuse and destruction.

Key choices:

- **Native Zig/C host:** Avoids a large managed-engine layer in this experiment. It also makes CPU command overhead easier to measure.
- **HLSL compute passes:** Keep spatial search, integration, constraint work, and result checks on the GPU.
- **Explicit synchronization:** Use GPU barriers for dependent passes and fences for resource lifetime. A fence signals completion; it does not prove a physics result is valid.
- **Indirect GPU work:** Generate dispatch counts and decide whether optional work is needed without copying each count to the CPU.
- **Timestamp queries:** Measure GPU work separately from CPU submission, waiting, rendering, and presentation.

**Distinct engineering value:** The work scheduler, memory ownership, and simulation are tested together. The useful result is measured end-to-end behavior, not a fast isolated kernel.

**Not implemented as a general service:** A complete autonomous GPU resource monitor, multi-client allocator, or general dependency scheduler. Current code has memory budget checks and a specialized fixed-pass pipeline. A general job graph remains planned.

## 4. Entity identity and GPU storage — G1

**Code:** `entity.zig`, `transaction.zig`, `storage.zig`, `storage.hlsl`, `layout.zig`, `layout.hlsl`.

Entities use **stable slot IDs with generation counters**. A dense index can change when live entities are compacted, while a stale handle must not become valid again after slot reuse. Separate maps connect slot IDs and dense storage.

The project compared three data layouts:

| Layout | Trade-off | Observed decision |
|---|---|---|
| Array of structures (AoS) | Simple per-entity access; extra data can enter a cache line. | Not selected for the measured pipeline. |
| Structure of arrays (SoA) | Passes can read only the fields they need. | **Selected** for the tested workload. |
| Array of structures of arrays (AoSoA32) | Groups fields into fixed-size tiles. | Tested; not selected as the default. |

The selected SoA layout stores entity fields in GPU buffers. Active entities can be compacted into a dense work list. A structural epoch invalidates cached active lists when the entity set or active policy changes.

Resource growth allocates new capacity, migrates live state, verifies maps, and retires old allocations only when owners finish. The earlier G1 evidence reports live processing at 10 million entities and growth to approximately 20 million **allocated slots**. The latter is a capacity test, not a 20-million-entity performance result.

**Measured historical G1 result:** Around **3.30 ms** for the selected 10-million-entity storage workload with 10% active entities. This is a storage pipeline result, **not full physics**.

**Innovation / value:** Generation-safe ECS identity, GPU-resident compaction, and verified lifetime-safe capacity changes work in one native pipeline. The individual methods are known techniques; the integration and evidence are the project contribution.

## 5. Memory limits, resource budgets, and failure control — G0/G1

**Code:** `runtime.c`, `storage.zig`, `physics.c`.

Before large allocations, the host computes buffer sizes with checked integer arithmetic. It compares required memory with a current DXGI budget and any user limit. The allocator records committed bytes, peak use, allocation counts, and retired resources.

The resource tests cover allocation failure, invalid dimensions, guard regions, delayed fences, structural changes, and cleanup. A failed allocation must not damage existing accepted state. Resource retirement must not release a buffer while the GPU or graphics queue still owns it.

**G0** established legal capacity and dispatch plans. For example, a historical 10-million-body plan used about **10.75 GB** under its assumptions. A legal memory plan is **not** proof of execution speed or a promise that all 10-million-body workloads fit every GPU.

**Open work:** A complete GPU resource broker with priorities and fair admission for independent simulation clients. Today, the system mainly applies budget limits and explicit ownership to its own workload.

## 6. Spatial indexing and contact discovery — G2

**Code:** `spatial.c`, `spatial.hlsl`, `spatial-schema.json`.

Testing compared a GPU spatial hash with a radix-based path. The selected hash uses an open-addressed lookup structure and a staged count, prefix, and scatter flow. The GPU uses it to find body pairs that may touch. Candidate pairs are not accepted contacts until the narrow phase checks them.

A broad-phase pipeline must avoid two errors:

1. **Missed contacts:** A pair reaches or crosses the contact boundary but is absent from the candidate set.
2. **False correctness claims:** A candidate count is reported as an actual resolved-contact count.

The GPU maintains counts, capacity guards, and checks of body-to-slot mapping. High-density tests validate contact coverage independently.

**Measured historical G2 result:** The hash path processed the specified 10-million-body workload with about **35 million verified contacts** in about **24.04 ms**. The compared radix path took about **37.67 ms** under that test. These results cover candidate/contact construction, **not resolution**.

**Innovation / value:** The broad phase was chosen by direct workload measurements. GPU-side contact counters and verification connect speed results to the work actually performed.

## 7. Contact graph and island construction — G3/G4

**Code:** `physics.c`, `physics.hlsl`, `execution-layout.h`.

Every body contact adds a constraint edge. The graph passes join bodies that depend on one another. A connected component forms a **collision island**. The solver may process independent islands at the same time.

The pipeline builds parent/root information, counts island members and constraints, scans offsets, and scatters data into contiguous ranges. Contact coloring separates constraints that must not write the same body concurrently.

This prevents a common GPU error: two threads update the velocity of the same body without an ordered resolution policy. It also exposes a cost: one very large island offers less simple parallel work than thousands of small independent islands.

The G4 billiards stress fixture has many **separate 16-ball tables**. It tests high population and many small contact islands. It does **not** show that a million mutually connected bodies can be solved efficiently.

**Open work:** Multi-workgroup solving for large islands, plus coordination costs, shared/global memory trade-offs, and bounded convergence under general contact graphs.

## 8. Projected contact solver — G3/G5

**Code:** `projected_solver.hlsl`, `physics.hlsl`, `physics-math.hlsl`.

The solver uses projected impulses. Normal impulses must not pull two bodies together. Friction impulses remain inside their configured bounds. The iteration loop measures a constraint residual and stops only when the result satisfies its tolerance, or when it reaches a work limit.

The solver stores accepted per-body state in 32-bit floating-point fields. Some sensitive intermediate calculations use 64-bit floating point. This helps avoid cancellation near strict convergence limits. The implementation checks momentum, energy, constraint residuals, and published-state consistency with independent tests where applicable.

A single-workgroup path can use local memory for a small island. Larger islands may use global GPU memory and need many synchronization steps. This is the main reason a large, tightly coupled graph can be much slower than the same number of independent entities.

### G5 convergence study: PGS and SOR

A local experiment added **projected successive over-relaxation (SOR)** with factor **1.995** for qualifying large islands. It improved difficult compressive chains. It did not improve all graphs.

| One connected island | PGS outcome / GPU time | SOR 1.995 outcome / GPU time |
|---|---:|---:|
| Chain, 64 bodies | Rejected / 19.58 ms | Accepted / 16.41 ms |
| Chain, 256 bodies | Rejected / 37.33 ms | Accepted / 31.63 ms |
| Chain, 1,024 bodies | Rejected / 187.60 ms | Accepted / 148.63 ms |
| Branching, 64 bodies | Accepted / 2.76 ms | Accepted / 14.21 ms |
| Dense, 64 bodies | Accepted / 1.98 ms | Accepted / 24.48 ms |
| Oblique/friction, 64 bodies | Accepted / 4.69 ms | Accepted / 9.88 ms |

These are the medians of **two cold, independent one-tick samples per configuration**, from the 2026-10-18 uploaded quick sweep. A rejected time measures an **attempt**, not a successful physics tick. This is not a sustained benchmark or an approved G5 performance target.

The results identify a clear trade-off: **fixed high relaxation rescues chains but often wastes thousands of iterations on other graphs**. For example, the 64-body dense fixture needs 107 PGS iterations and 3,232 SOR iterations. No one global factor has been qualified for all tested contact patterns.

### G5 adaptive relaxation trial — rejected (2026-10-18)

A new local headless sweep compared **PGS**, **fixed SOR 1.995**, and one **adaptive residual-based** policy. It used ten deterministic cold compressive fixtures and two independent one-tick samples per solver and fixture (**60 runs**). The CSV matches all 30 JSON summary entries. Every accepted run passed the recorded independent invariants, and rejected attempts reported verified rollback.

| One connected island | PGS GPU p50 | Fixed SOR GPU p50 | Adaptive GPU p50 | Adaptive outcome |
|---|---:|---:|---:|---|
| Chain, 64 bodies | Rejected / 19.67 ms | Accepted / 15.55 ms | **Accepted / 2.39 ms** | 366 iterations |
| Chain, 256 bodies | Rejected / 39.39 ms | Accepted / 33.34 ms | **Rejected / 35.19 ms** | Reached 4,096 iterations |
| Chain, 1,024 bodies | Rejected / 188.93 ms | Accepted / 150.51 ms | **Rejected / 175.11 ms** | Reached 4,096 iterations |
| Branching, 256 bodies | Accepted / 15.26 ms | Accepted / 28.60 ms | Accepted / 15.63 ms | Near PGS cost |
| Dense, 64 bodies | Accepted / 1.94 ms | Accepted / 28.23 ms | Accepted / 1.85 ms | Near PGS cost |
| Oblique/friction, 256 bodies | Accepted / 34.95 ms | Accepted / 34.68 ms | Accepted / 33.92 ms | Near PGS cost |

The adaptive policy converged in **16 of 20** attempts; fixed SOR converged in **20 of 20**, and PGS in **14 of 20**. It reduced the 64-body chain solver work substantially, but it lost required convergence for the larger chains. Reported rejected GPU times are failed **attempt costs**, not simulation throughput.

**Decision: REJECT ADAPTIVE.** The submitted local results state that the pre-change source policy and production shader binaries were restored. The previous fixed-SOR policy remains the local working baseline; the restoration was **not followed by a separate GPU rerun**. No code or binary change was introduced by this documentation update.

**Evidence:** User-uploaded `results(2).json` and `results(2).csv`; quick run, 2026-10-18; 2 samples per case, 4,096-iteration limit, no GBV or sustained workload claim. These evidence files are **local**, not GitHub CI. Recorded sweep SHA-256: `81de61132ef41cd1937d6c4f591e4cb528732b8d6`.

**Next action:** Use a **headless residual-trajectory diagnostic** on chain sizes 64, 256, and 1,024 to find why adaptive relaxation stalls. Evaluate one safeguarded fallback or restart rule, with a strict work budget and both fixed baselines unchanged. Run a single consolidated sweep. Do not launch the viewer, capture screenshots, or start multi-workgroup solver development yet.

### G5 bounded-restart candidate — conditional correctness pass (2026-10-18)

Production remains policy 1: the existing PGS/fixed-SOR behavior (not a qualified G5 result). Policy 2 is
the rejected residual-adaptive experiment. Policy 3 adds one bounded restart
and is retained as an **opt-in correctness candidate**, not a G5 qualification
or a production performance improvement.

The experiment reports retaining the SoA storage, spatial/contact pipeline,
contact graph, global tick, immutable free-state inputs (not strict immutable
source-buffer publication), projected normal/tangent constraints, rounded-state KKT
tolerances, validation, work limits, and rollback are preserved. The change is
local to the existing GPU island solver; it creates no scheduler or CPU solve.

### Diagnosis

GPU traces record every 64-iteration residual window and relaxation change.
The 64-body chain settles near omega 1.929 and converges without a reduction.
For 256 bodies, a window contraction ratio of 2.633 at iteration 384 halves
the excess relaxation from approximately 1.995 to 1.4975. For 1024 bodies,
reductions occur at iterations 320 and 3200 (ratios 1.486 and 13.967).
The controller mistakes nonmonotonic SOR residual transients for sustained
instability. It then restores relaxation too slowly: the final factors are
1.9328125 and 1.9638911, respectively. Both exhaust 4096 iterations.
Independent contact/impulse/oracle checks and exact rollback pass; this is a
relaxation-control failure, not evidence of incorrect contact equations.

### Bounded fallback and measured decision

Policy 3 spends at most one eighth of the island's existing iteration/work
budget on adaptation. If it has not converged, it clears only that island's
impulses, restores its immutable free velocities, and runs fixed SOR 1.995 for
the remaining budget. There is at most one restart, no new allocation or
mid-solve readback, no size/topology/fixture rule, and no tolerance or limit
increase. A remaining-budget failure still rejects and rolls back normally;
this is not a universal convergence guarantee.

One serialized quick batch: two cold one-tick trials per configuration, plus
six instrumented chain trials. The diagnostic automatically reproduced the
old-policy failures before allowing candidate execution. All 20 candidate
and 20 fixed-SOR benchmark trials converged; PGS converged in 14 and rejected
six at 64/256/1024 bodies. The reviewed JSON contains 60 timing runs and 6
additional diagnostic runs; all 30 summary medians agree with their raw samples.
All 54 accepted benchmark runs report accepted-state invariant checks, and all
6 rejected runs report verified rollback. Actual island/contact coverage, KKT, impulse
reconstruction, accepted-state invariants and rejected-state rollback passed.
There were no timeouts or final audit errors. Thirteen sweep unit tests pass.

| Chain bodies | Fixed SOR GPU p50/p95, ms | Candidate GPU p50/p95, ms | Candidate iterations |
|---:|---:|---:|---:|
| 64 | 15.69 / 15.72 | 2.52 / 2.57 | 367 |
| 256 | 33.76 / 33.89 | 39.78 / 39.85 | 4036 |
| 1024 | 148.51 / 149.50 | 173.56 / 177.48 | 4026 |

The fallback recovers every previously converging configuration, but discards
useful adaptive/PGS progress on slower successful networks. At 256 bodies,
branching costs 34.39 ms versus PGS 15.86 ms, and oblique/frictional costs
52.64 ms versus PGS 31.14 ms. Keep production unchanged. The next target is
a residual-informed restart trigger that avoids these unnecessary restarts;
the 1024-body global-memory island solve remains the dominant cost.

### Decision breakpoint: remove unnecessary restarts (policy 4)

Retain policy 4 as an opt-in successor to policy 3. At the same one-eighth-budget
checkpoint (iteration 512 with the unchanged 4096 limit), restart only when
the minimum absolute projected residual in the last complete 64-iteration
window is at least 0.8 times the preceding window minimum. This reuses the
controller's existing poor-contraction threshold. Improving windows preserve
their impulses and velocities; there is no later forced restart or increased
budget. Restarted islands use the same single clean fixed-SOR fallback.
The rule has no topology, size or fixture lookup. All KKT, projection, friction,
energy/momentum and rollback checks remain unchanged.

Saved policy-2 traces showed checkpoint ratios 1.3123 and 0.9731 for the failing
256/1024 chains. In the new batch, candidate ratios were 0.9956/0.9639 for those
chains (restart), 0.5391 for branching-256 and 0.3903 for oblique-256 (preserve).
All ten instrumented candidate histories satisfy the restart decision audit.

One automated `python sweep_g5.py quick --trace-restarts` invocation ran 17
unit tests, built once using verified dependency caches, then serialized 80
uninstrumented timing trials and ten candidate trace checks. Every candidate,
policy-3 and fixed-SOR timing trial converged (20 each); PGS converged in 14
and rejected six. All ten candidate trace cases converged. Full contact/island
coverage, unchanged invariants and rejection rollback passed; no timeouts or
audit errors occurred. No passing case was rerun manually.

The predeclared retention rule requires both equal-fixture geometric mean
and sum of GPU p50 times to be no worse than policy 3, with no lost convergence.
The measured ratios were 0.8690 and 0.8650; summed CPU submission medians were
0.9876 of policy 3. Branching-256 improves from 33.63 to 15.57 ms and
oblique-256 from 56.85 to 30.66 ms. Candidate chain-256/1024 still require
4036/4027 iterations, with GPU p50/p95 39.78/39.92 and 171.52/171.97 ms.
Small individual timing increases remain visible in the raw comparison; two
samples are exploratory, not a tail-latency or significance claim.

The remaining dominant cost is the 1024-body one-workgroup/global-memory solve:
170.30 ms of its 171.52 ms complete tick. The restart still discards 512
iterations on hard chains. Production stays policy 1; no broader G5 approval
is implied. **Evidence:** User-uploaded `results(4).json` and `ENGINE_ARCHITECTURE(2).md` (2026-10-18), saved locally in the Codex workspace under `dev-test-results/g5-sweep-20261018T080015570617Z/`. The companion CSV and residual-traces CSV are referenced in the handoff but **not available on GitHub** or independently inspected here. The raw JSON contains full trace events, test statuses, CPU/GPU timings, source/build hashes, and measured candidate results. No GPU runs were executed during this document update.

**Gate and provenance note:** These results represent a local opt-in solver experiment. They do not establish that the policy-4 HLSL implementation has been committed to the linked GitHub branch. They are not a sustained-simulation qualification, and the 80 two-sample timing runs cannot establish stable p95 latency. G5 remains **NOT QUALIFIED**.

### Reproduction and evidence

Run `python sweep_g5.py quick --diagnose-adaptive`. All builds finish before
GPU cases execute sequentially under the existing workflow lock. Traced
diagnostic runs are separate from uninstrumented timing trials. The test-only
trace uses checked, bounded unused contact-record space; missing windows or
insufficient room fail the diagnostic without truncating simulation work.

Full results, CPU submission times, source/binary hashes and raw exports
were saved **locally** under `dev-test-results/g5-sweep-20261018T074517651930Z/`.
The user supplied `results(3).json` and `ENGINE_ARCHITECTURE(1).md` for this
review. The separate CSV and residual trace exports were referenced by the
handoff but were **not uploaded or committed to GitHub**. Therefore those
exports have not been independently inspected in this documentation update.

The batch required a trace-decoder repair for the GPU's distinct float32 and
float64 encodings of the 1.995 literal. `--resume` verified compiled artifacts,
reused 42 completed GPU cases, and ran only the 24 unexecuted cases, without
rebuilding. Original summaries retain those decoder failures; final trace
repairs used saved exports only. Timing controls therefore precede the resumed
candidate trials. Two samples make p95 merely the maximum, not a tail-latency
claim. No GUI, packaging, sustained campaign or broader gate approval occurred.
**Scope:** This evidence concerns local uncommitted solver experiments, not
code shipped on `main` or the playable GitHub branch. The source and compiled
binary hashes are reported in local JSON but binaries are not available here
for independent execution. Neither G5 nor the candidate is production-qualified.

### G5 global-memory solver profiling and body-cache experiment — REJECT (2026-10-18)

**Tested change:** A bounded group-shared body-state cache for at most 1,024 connected bodies, in `projected_solver.hlsl`. It keeps current work velocities and sleep state in shared memory, uses the existing global-memory path above that limit, and leaves other solver policies available for the sweep. The compiler reported 30,728 bytes of group-shared memory for this variant. The cache was tested behind `G5_BODY_CACHE`; the delivered default remains **0** and production relaxation policy remains **1**.

**Verification:** One serialized headless `python sweep_g5.py quick --profile-global` run produced 100 uninstrumented timing trials (ten deterministic fixtures × five solver configurations × two cold attempts) and 22 separate profiling/policy/boundary probes. The package includes 22 passing unit tests and archived per-run results. All **20 cached policy-4 trials converged** with passing invariant checks; across the 100 timing trials there were **94 accepted** and six expected PGS rejections with verified rollback. All 50 JSON summary medians match the recorded samples. A 1,025-body boundary probe used the global fallback and rejected/rolled back as expected.

| Connected island | Policy-4 global p50 | Cached policy-4 p50 | Change |
|---|---:|---:|---|
| Chain, 16 bodies | 3.53 ms | 4.30 ms | **21.7% slower** |
| Chain, 64 bodies | 3.09 ms | 3.77 ms | **21.9% slower** |
| Chain, 256 bodies | 37.16 ms | 37.68 ms | 1.4% slower |
| Chain, 1,024 bodies | 170.13 ms | **152.69 ms** | **10.3% faster** |
| Branching, 256 bodies | 19.30 ms | 18.89 ms | 2.1% faster |
| Oblique/friction, 256 bodies | 31.88 ms | 32.58 ms | 2.2% slower |

The 1,024-body **solver stage** changed from 167.47 ms to 150.47 ms; iterations changed from 4,026 to 4,025. The cache improves the heavy chain but harms the equal-fixture geometric-mean GPU p50 by **4.25%** (ratio 1.04253), despite reducing the sum of fixture medians by **4.82%** (ratio 0.95176). It therefore **fails the predeclared two-part retention rule**. Two samples per fixture are not enough to claim a statistical or p95 gain.

**Cost analysis and boundaries:** Rejected, rollback-verified PGS diagnostic probes yielded a complete-solver fit of **45.79 microseconds per iteration** and a **1.687 ms** fixed/intercept term. A synthetic barrier/reduction probe measured 0.674/0.811 ms for 128/512 virtual iterations; it is not an accepted physics solve or an additive synchronization share. Counted real runs recorded about **45,800 device barriers** and **36,240 group barriers**. Instrumented source-level body accesses imply about **1.100 GB of logical global working-velocity access** before caching, but compiler-elided loads, cache hits, real DRAM traffic, and stall time are not known. A bracketed empty-work queue interval of 0.837 ms contains multiple effects and is not pure dispatch overhead. Nvidia Nsight GPU performance counters were **not accessible** owing to permissions; no hardware-memory, FP64 utilization, or actual stall-cause attribution is established.

**Decision:** **REJECT as a general default.** Preserve policy 1 and `G5_BODY_CACHE=0`. The changed shader and analysis scripts are provided only in the local handoff; this documentation update does not commit or activate shader changes. G5 remains **NOT QUALIFIED**.

**Evidence:** Supplied `G5-Global-Solver-Cost-Handoff-20261018T090324676154Z.zip`; included `evidence/results.json`, `evidence/results.csv`, `evidence/profile.csv`, per-run JSON/logs, compiler diagnostics, and source. The archived and tested `projected_solver.hlsl` files match byte-for-byte; its SHA-256 matches the result manifest. A setup-only DXIL parser error, recorded in `setup-failure.json`, was fixed before GPU execution; the resumed run reused compiled artifacts. None of these local evidence files are claimed to be GitHub CI. The ZIP's `docs/ENGINE_ARCHITECTURE.md` is a **short experiment excerpt**, not this complete living record.

**Next action:** Investigate the high cost per solver iteration, separating arithmetic, synchronization, and memory behavior as far as is possible with headless CLI and static DXIL analysis. If hardware counters remain unavailable, report **UNVERIFIED** rather than guessing. Test at most one narrowly justified correction against complete-tick baselines with the same automated quick sweep.

### G5 per-iteration optimization — baseline recovery blocked, evidence located (2026-10-18)

**Failure report:** The user-supplied `G5-baseline-recovery-blocker.zip` contains a `BLOCKED` status, a documentation-only patch and a short status manifest. Codex could not reconstruct the measured G5 solver baseline after cleaning its local workspace. Its restored checkout at `3a29fc0ec9ff9ac54c0680e9130405368700074c` has the earlier fixed-relaxation shader but lacks `sweep_g5.py`, `profile_global.py`, the measured policy-4 shader and raw evidence. The blocker reports **no** GPU sweep, production shader change or optimization measurement. Its cited documentation commit `49fd7980253d69c64db4918c5a0ca113fd47d622` belongs to the local patch; this entry does not assert that the local commit was published.

**Evidence recovery:** The exact original `G5-Global-Solver-Cost-Handoff-20261018T090324676154Z.zip` is still available in the conversation uploads. Its SHA-256 is `07dd2be67af66faf089bdc726feb1b0b4d7cdd59a7250a8fcf7d4acb327c0a18`, exactly the value required by the blocker. ZIP integrity passes. It contains `projected_solver.hlsl`, `sweep_g5.py`, `profile_global.py`, unit tests, deterministic fixture files and archived raw results, CSV, traces and build logs. The shader matches its archived tested copy and the source manifest at SHA-256 `f9b93e98d3fb78944ae6547530d77e94cf29013ca61313af41d3448194bb05f9`. Its compile-time defaults remain **policy 1** and **`G5_BODY_CACHE=0`**; historical policy-4 tests require an explicit `G5_RELAXATION_POLICY=4` compile setting.

**Dependency check:** A hash-matched `profile_islands.py` was found in the previous G5 convergence handoff and a hash-matched `dev_test.py` in the requalified billiards handoff. In total, **seven** workflow files and **21 of 25** measured engine source files were recovered with matching SHA-256 hashes. Four baseline source files (`asset_path.h`, `physics.h`, `playground-layout.h`, `playground.hlsl`) have **not** been recovered from the accessible uploaded archives. They must be verified against the isolated target checkout before claiming a fully reproduced source baseline. The test binaries and original GPU execution environment are not bundled.

**Artifact:** The newly prepared `G5-Baseline-Recovery-Kit-20261018.zip` contains the original intact archive, hash-matched dependencies, available source snapshots, a manifest and a read-only local verification script. The kit passed an offline SHA-256 and ZIP integrity check. It is a recovery **handoff**, not a tested rebuilt baseline or a code patch.

**Decision: BLOCKED pending isolated baseline reconstruction.** Do not substitute an earlier solver's measurements for the policy-4 baseline, install unverified files into the user's dirty working tree, or claim another per-iteration optimization. Once all source hashes and build settings match, run one serialized headless quick sweep with the original unchanged shader to establish the Windows D3D12 baseline. Then profile or implement one semantics-preserving per-iteration change. G5 remains **NOT QUALIFIED**; G0–G4 status is unchanged.

### G5 isolated baseline restoration — source/behavior PASS (2026-10-18)

**Recovery:** An isolated Windows checkout rebuilt the measured G5 command-line baseline from the recovery kit. The package `G5-Baseline-Restored-20261018.zip` includes the rebuilt source snapshot, `projected_solver.hlsl`, the G5 sweep, its fixture binaries, raw run JSON and per-run exports, CSV summary, compilation logs, verifier, and comparison report. The original project workspace was not altered as part of this recovery.

**Source and build checks:** The restored manifest reports **25 of 25 source files** and **6 of 6 workflow files** matching the archived SHA-256 hashes, including all four previously missing sources (`asset_path.h`, `physics.h`, `playground-layout.h`, `playground.hlsl`). The ZIP source hashes match the manifest. The restored shader matches the saved tested shader at SHA-256 `f9b93e98d3fb78944ae6547530d77e94cf29013ca61313af41d3448194bb05f9`. All shader-output hashes match the archived baseline, with G5 policy 4 compiled as `G5_RELAXATION_POLICY=4` and `G5_BODY_CACHE=0`. The ordinary production default remains policy 1 and cache-off.

**Behavior test:** Recorded Windows commands ran **33 headless workflow/unit tests** successfully; the sweep's focused 17 tests also passed (these may overlap and must not be added as independent tests). The serialized quick sweep recorded **80 single-tick GPU trials**, ten connected-island fixtures, four solver configurations, and two cold samples per case. All **20 policy-4**, **20 policy-3**, and **20 SOR** trials converged; PGS converged in **14 of 20**, with six expected rejections and independently checked rollback. All **74** accepted trials passed the supplied physical invariant checks. The sweep returned exit code 1 because expected PGS rejection cases are treated as failures by its aggregate exit policy; this is not a claim that the recovery itself failed. The CSV agrees with all 40 JSON summary rows and their 80 recorded p50 sample values.

| Policy-4 workload (one connected island) | Prior archive p50 | Restored Windows p50 | Result |
|---|---:|---:|---|
| Chain, 64 bodies | 3.09 ms | **2.47 ms** | Converged, 367 iterations |
| Chain, 256 bodies | 37.16 ms | 38.40 ms | Converged, 4,036 iterations |
| Chain, 1,024 bodies | 170.13 ms | **167.94 ms** | Converged, 4,026 iterations |
| Branching, 256 bodies | 19.30 ms | 18.24 ms | Converged, 1,195 iterations |
| Oblique/friction, 256 bodies | 31.88 ms | 37.41 ms | Converged, 1,082 iterations |

These are two cold independent ticks per case. Differences between two samples are not evidence of sustained speedups or latency quantiles; p95 equals the larger of two samples.

**Non-identity limitations:** The rebuilt `physics.exe` SHA-256 differs from the historical executable (`b68e82b173659046a93767444ebaa9a90d6d222d473e34375ecf187a0fa1836e` versus `fbc98450e31ffe5eb452a58ab3457aa1f22319d1b1d26d2de65dfcc7a7dd0451`). The archived historical executable bytes are unavailable; the cause is **UNVERIFIED**. The archived/new comparison records **156 numerical field differences** in per-run KKT values, iteration counts and energy/momentum roundoff, plus **23 contact-color count differences**; the maximum iteration difference is **444**. There are **zero structural/acceptance mismatches** in status, body/contact/island counts, invariant pass/fail and rollback. The evidence therefore supports **source-and-behavior restoration, not bitwise deterministic replay**. GPU debug-layer/GBV and sustained multi-tick qualification were not repeated.

**Decision: RECOVERY PASS; G5 STILL NOT QUALIFIED.** The missing-file blocker is closed for controlled research. Use the restored isolated checkout as the next matched before/after baseline; retain the exact source hashes, compile flags, shader hashes and fixtures. Do not compare isolated two-sample timings across different builds as if they were performance qualification. Do not commit experimental policy 4 to production based on this recovery alone.

**Next action:** Diagnose the executable hash mismatch through recorded compiler/linker/build inputs **without changing solver mathematics or doing another broad GPU run**. Establish the current executable as a stable local baseline, then investigate one measured cost per iteration and compare before/after in **one headless CLI sweep**. Preserve the original workspace and update this document at the next decision.

**Evidence:** User-supplied `G5-Baseline-Restored-20261018.zip`, including `recovery-manifest.json`, `evidence/preflight/provenance.json`, `evidence/sweep/results.json`, `results.csv`, `recovery-comparison.json`, Windows logs and exported GPU state. ZIP integrity and recorded summary data were checked off-line; the GPU run was recorded on Windows, not repeated in this review environment. Local handoff evidence is not GitHub CI evidence.

### G5 repeated-body-load removal in solver measurement — RETAIN (2026-10-18)

**What changed:** The original `measure()` fetched the bodies for the contact's tolerance test, then fetched them again through `relative()` for normal and tangential projected residuals. The contact state is not written between those reads. The new `measureRelative()` reuses the already loaded `Body a` and `Body b`, with the same explicit float32 rounding before FP64 relative-speed calculations. The `applyColor()` path is unchanged; it still reloads the bodies after a normal impulse before applying the tangential impulse. The change does not alter the contact graph, constraints, projection, solver iteration/work budget, synchronization barriers, KKT acceptance rules, or rollback.

The new compile-time selector is `G5_REUSE_MEASURE_BODIES` (0 = original, 1 = reuse). The **retained source defaults to 1**. The retained source SHA-256 is `39d7d5e606dfad1cbd71de04e1de68a3d7d008e35f235bfdc01df8814edc233f`; the separately tested candidate snapshot has SHA-256 `f060d6975f6d82bd92145767cfb8a6c518ed14eecc55ec712c56882749f488bb` because the default macro was switched after testing. The recorded final production-policy `ph_ready` and `ph_solve` shaders were rebuilt and their hashes matched the policy-1 candidate shader results exactly. The default relaxation policy remains **1**, and body caching remains **0**. No new GPU correctness tests were run after only changing that compile-time default.

**Static shader evidence:** For policy 4, `ph_solve.dxil` includes **225 → 191** static buffer-load instruction sites, **71 → 55** double-assembly sites and **157 → 153** FP64 arithmetic instruction sites; shader barrier sites remain **20**. These counts describe disassembled instruction sites, not physical memory transactions, cache misses or real stall time. Fresh unchanged controls for policy 0/1/3/4 reproduced historical archived `ph_solve.dxil` hashes, and all five policy configurations used the same fresh linked CLI host executable across the two arms.

**Matched Windows headless test:** One `python sweep_solver_cost.py quick` batch ran 33 existing unit tests, compiled the control and candidate variants, and executed **200 cold single-tick trials** (10 fixtures × 5 policies × 2 variants × 2 attempts). All trials completed without timeout. Independently recomputing all 50 JSON summary medians from the 200 recorded runs found no mismatches. Each arm produced **90 accepted and 10 expected rejected** trials; the rejection breakdown is six PGS and four original-adaptive-policy cases. All accepted trials reported invariant checks passed, and each rejection reported verified rollback. The contact/island counts, acceptance status, KKT bounds and work limits remained valid. This is recorded Windows execution evidence, **not** an independently rerun GPU test.

| Tested policy 4, one connected 1,024-body chain | Unchanged control | Body snapshot reuse |
|---|---:|---:|
| Complete GPU tick p50 | 167.33 ms | **162.99 ms** |
| Solver-stage p50 | 165.35 ms | **161.12 ms** |
| CPU recording/submission p50 | 2.928 ms | 2.846 ms |
| Solver iterations, two trials | 4,026 / 4,025 | 4,026 / 4,027 |
| Actual contacts / largest island | 1,023 / 1,024 | 1,023 / 1,024 |

**Decision rule:** Retain only if all correctness/rollback conditions pass and both the geometric mean and sum of complete-tick GPU p50 improve across (a) the ten policy-4 fixtures and (b) all 45 accepted-policy configurations. The audited policy-4 geometric-mean/sum ratios are **0.962547 / 0.964774**; the all-accepted-policy ratios are **0.983971 / 0.953917**. Both predeclared aggregate performance tests pass. **Decision: RETAIN** the narrow source change.

**Limits and observed regressions:** Some individual workloads regressed: branching-64 policy 4 went from **3.129** to **3.241 ms**, and dense-256 from **11.168** to **11.580 ms**. Solver coloring and iteration counts also vary slightly between runs. Two cold samples do not support a robust p95 or sustained-performance claim. The 1,024-body connected chain still spends roughly **161 ms** in its solver, with about **4,026** iterations. The division between FP64 arithmetic, barriers and actual memory stalls remains **UNVERIFIED**.

**Executable reproducibility:** A newly built unchanged CLI had SHA-256 `237c22371b75c76ffed9cc5c50b4f4fbbe201bd77e7539f49c0466b4d7edddbc`, versus the recovered local executable `b68e82b173659046a93767444ebaa9a90d6d222d473e34375ecf187a0fa1836e`. Local PE section hashes match for every section except `.buildid`, providing a concrete metadata explanation for that local rebuild difference. The much older archived executable fingerprint `fbc984...` cannot be explained without its original bytes, build logs and linker inputs.

**Evidence:** User-supplied `G5-Solver-Snapshot-Reuse-20261018.zip`: source and baseline HLSL, `change.patch`, static DXIL dumps, `evidence/matched-quick/results.json` and `results.csv`, 200 per-run exports, `retained-build.json`, 33-test log, linker/PE provenance and source architecture excerpt. ZIP CRC verification passed; recorded source hashes and summary medians were checked. The archive's source doc is an **experiment copy**; this section is integrated into the full living GitHub record instead. **No experimental solver code has been pushed to GitHub by this review. G5 is not qualified.**

### G5 skip overwritten preliminary residual — RETAIN LOCALLY (2026-10-18)

**Change:** During `ph_solve`, every eighth solver iteration and the final allowed iteration must reconstruct the per-body velocities from the free state and accumulated impulses. That path runs a mandatory projected-residual measurement and uses its result for the acceptance check. The prior hot loop also measured the residual **immediately before** these mandatory reconstructions, even though the subsequent measurement replaced both residual outputs. With `G5_SKIP_OVERWRITTEN_RESIDUAL=1`, the candidate omits only that redundant preliminary scan. The device/group barrier before reconstruction remains. Preliminary scans on all other iterations, and the post-reconstruction KKT measurement, are unchanged. There is no change to contact equations, FP64 expressions, impulse projection, color order, iteration/work limits, validation, rollback or adaptive/fallback policy rules.

At 4,026 iterations, the source-level logic skips 503 preliminary measurements and approximately 4,024 group-reduction barrier executions while keeping all required reconstruction checks. These are **source execution counts, not measured GPU barrier stalls or DRAM transactions**. The candidate does not reduce the required 4,026 iterations. Static DXIL instruction-site counts remain **191 buffer loads, 55 double assemblies, 153 FP64 arithmetic operations and 20 barriers** for policy 4; this optimization avoids executing part of the compiled code instead of removing static instructions.

**Matched headless evidence:** The single `python sweep_solver_cost.py quick --skip-overwritten-residual` Windows batch recorded **200 timing trials** (ten deterministic one-tick fixtures × five policies × two compile flags × two cold samples) plus six separate chain residual traces. Each matched arm contained **90 accepted solves** and **10 expected rejections** (six PGS and four earlier adaptive-policy attempts). The recorded independent accepted-state checks passed; rejected attempts verified rollback. Trace checks reproduced the expected 64-, 256- and 1,024-body chains without changing accepted/rejected decisions. All **50** JSON summary rows were independently recomputed from the trial data and matched the CSV, with no mismatches. **34** workflow/unit tests passed in the final recorded run. No graphical tests or Windows GPU execution occurred during this documentation review.

| Policy-4 connected island | Existing snapshot-reuse GPU p50 | Skip-overwritten-scan GPU p50 | Outcome |
|---|---:|---:|---|
| Chain, 64 bodies | 2.98 ms | **2.33 ms** | 367 iterations in both arms |
| Chain, 256 bodies | 37.74 ms | **33.46 ms** | 4,035 iterations in both arms |
| Chain, 1,024 bodies | 165.61 ms | **155.86 ms** | 4,026 iterations in both arms |
| Branching, 64 bodies | **3.49 ms** | 3.78 ms | **Regression** |
| Oblique/friction, 256 bodies | 34.37 ms | **31.69 ms** | Accepted in both arms |

The **1,024-body solver stage** changed from **163.33 to 153.93 ms**. The retained candidate met the predeclared quick-balance test: policy-4 geometric-mean and total-p50 ratios were **0.940693** and **0.932529**; the corresponding ratios across **45 accepted-policy configurations** were **0.997168** and **0.971424**. The broad geometric-mean improvement is **only 0.28%**. Two cold trials per configuration cannot establish a general or sustained-performance gain; a reported quick p95 is merely the higher of two samples. Dense-64 and branching-64 policy-4 cases were slower.

**Source integrity and defaults:** The baseline snapshot-reuse shader SHA-256 is `39d7d5e606dfad1cbd71de04e1de68a3d7d008e35f235bfdc01df8814edc233f`. The source compiled in the explicit matched experiment has `G5_SKIP_OVERWRITTEN_RESIDUAL=0` as its default and SHA-256 `a9a8408f46da936140b8e2e6302f49e4de25504289f424d9be6946478f0b3697`; test commands override the flag to 0 or 1. The retained shader source differs only in that macro's **default value of 1**, and has SHA-256 `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24`. This difference is intentional; the original test-source SHA does **not** equal the retained file's SHA. The retained policy-1 `ph_ready` and `ph_solve` shader hashes match the explicitly tested candidate variant according to the Windows build log. Relaxation policy **1**, `G5_BODY_CACHE=0`, and `G5_REUSE_MEASURE_BODIES=1` remain the retained defaults. The user-supplied preservation report states that all **313 original tracked files and uncommitted status** remained unchanged in the original workspace; work took place in an isolated copy.

**Decision: RETAIN UNDER THE QUICK RULE, NOT RELEASE-QUALIFIED.** Keep the conditional skip in the local experimental shader. It reduces known redundant execution, but it does not resolve the main cost of ordered FP64 contact/color iterations and slow convergence. The 1,024-body solver still takes **about 154 ms per tick**. G5 remains **NOT QUALIFIED**. No code, shader binaries or test artifacts are committed to GitHub by this documentation checkpoint.

**Evidence:** User-uploaded `G5-Skip-Overwritten-Residual-20261018.zip`, including `source/projected_solver.hlsl`, `baseline/projected_solver.hlsl`, `change.patch`, `evidence/results.json`, `results.csv`, full per-run exports and residual traces, compiled DXIL listings, Windows unit logs, retained-build provenance, and workspace-preservation record. Archive integrity, diff scope, summary data, and available SHA-256 values were checked offline. These are local Windows recordings, **not GitHub CI or an independently rerun GPU qualification**.

### G5 early residual restart — REJECT (2026-10-19)

**Hypothesis:** The residual-gated policy 4 restarts a hard connected island at iteration 512, after using one eighth of its 4,096-iteration budget. A restart might save solver work if the current relaxation has failed to contract the residual. A new **opt-in policy-4-only** check restarts at an earlier complete 64-iteration window after **two consecutive poor-contraction windows** (contraction at least 0.8), once relaxation is above 1 and the settling period has ended. A fast-contraction window resets the evidence. The original iteration-512 checkpoint remains as a fallback; no topology name or body-count rule was used.

**Physics contract:** The experiment preserved the contact equations, normal/tangent impulse projection, FP64 computations, original work and iteration limits, residual/KKT and energy/momentum checks, and rollback. The earlier retained `G5_REUSE_MEASURE_BODIES=1` and `G5_SKIP_OVERWRITTEN_RESIDUAL=1` options remained enabled. No solver policy other than policy 4 was changed. The trace reader gained strict verification of early restart timing and settled poor-residual windows.

**Evidence audit:** The local Windows handoff `G5-Early-Restart-Rejected-20261019.zip` includes 200 serialized, cold single-tick timing runs across ten configurations, five policies, two arms and two samples per arm. It also includes 40 independently instrumented trace trials. **Each arm accepted 90/100 timed trials and rejected 10/100** (six expected PGS rejections and four expected original-adaptive-policy rejections). All **180** accepted trials reported passing invariant checks; all **20** rejected attempts reported verified rollback. All 40 trace trials converged, and the handoff reports **37 passing headless unit tests**. The **50 JSON summary medians** were independently recomputed from the raw runs and checked against the saved CSV, with no mismatches. This is recorded Windows GPU evidence; the D3D12 tests were not repeated during this review.

**Trace findings:** Policy 4 restarted only the 256- and 1,024-body chains in the traced set. In both, restart moved **512 → 256** iterations. Policy-4 trace restart counts stayed at **two per arm** across ten fixtures, while policy-3 remained at **four per arm**. The 1,024-body chain fell from about **4,025 to 3,769** solver iterations. Counts from instrumented traces are **not per-timing-trial measurements**. No 64-body chain or dense/oblique fixture triggered an early policy-4 restart in the reviewed traces.

| Policy-4 workload, one connected island | Retained control GPU p50 | Early-restart GPU p50 | Outcome |
|---|---:|---:|---|
| Chain, 64 bodies | 2.35 ms | 2.35 ms | No early restart |
| Chain, 256 bodies | 32.74 ms | **30.91 ms** | 4,035 → 3,779 iterations |
| Chain, 1,024 bodies | 150.31 ms | **147.05 ms** | 4,025/4,024 → 3,768/3,770 iterations |
| Dense, 64 bodies | **1.86 ms** | 2.05 ms | Slower without restart |
| Dense, 256 bodies | **9.70 ms** | 10.15 ms | Slower without restart |
| Oblique/friction, 256 bodies | **28.79 ms** | 32.65 ms | Slower without restart |

**Performance decision:** The unchanged four-part retention rule requires **both** the geometric mean and summed complete-tick GPU p50 to improve for (1) all ten policy-4 fixtures and (2) all 45 previously accepted policy configurations. Policy-4 geometric-mean ratio was **1.0097496** (0.97% worse) and sum ratio **0.9944305** (0.56% better): the candidate **failed**. Across all accepted configurations, geometric-mean/sum ratios were **0.9929693 / 0.9938164**, but they cannot override the failed policy-4 criterion. Some fixtures with no change in restart behavior grew slower. With two cold trials and variable contact-color ordering, these timing differences cannot be attributed to the new condition with high confidence. Static DXIL instruction-site counts were unchanged for policy 4; no claim about DRAM, occupancy or hardware stall savings is justified.

**Decision: REJECT; RESTORE PREVIOUS SOLVER.** The archive's retained `source/projected_solver.hlsl` has SHA-256 `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24`; its experimental `evidence/tested-projected_solver.hlsl` has SHA-256 `b57f6011133a647bf4c787913ed70a8be484923d27edd69a6c1e862ec10c449b`. The recorded restoration report confirms byte-for-byte rollback of the active shader, rebuilt policy-1 and policy-4 shader hashes matching controls, and preservation of the original workspace (388 checked files and dirty status unchanged). This architecture-document update does **not** publish experiment shader code. Keep the production policy-1 default and policy 4 opt-in. G5 remains **NOT QUALIFIED**.

**Next decision:** Before another restart heuristic, isolate run-to-run contact coloring and GPU timing variation by comparing fixed-input traces and matched configuration controls. Quantify whether a smaller restart budget offers a repeatable net improvement across the existing ten fixtures **without** weakening correctness criteria. If the variation cannot be controlled, prefer a targeted solver-algorithm study over threshold tuning. Do not run a long or GUI-based campaign.

### G5 identical-control measurement repeatability — MEASURED; solver unchanged (2026-10-19)

**Why this test exists:** Several prior candidate sweeps showed GPU-time and iteration differences even when the restart behavior did not change. To isolate confounding factors, a local Windows measurement tool ran **identical executable/shader controls labeled A and B**. No solver code, shader, relaxation threshold, acceptance criterion, or default changed. A/B labels carry **no optimization**.

**Test method:** `measure_repeatability.py` reuses the recovered G5 fixture, execution and independent audit. It verifies the same CLI executable, all shader files, ten frozen fixture binaries, source hashes and device identity before/after execution. Four paired AB/BA blocks per fixture produced **80 serialized cold one-tick GPU runs** on an **NVIDIA GeForce RTX 4070 Ti SUPER**: ten topologies/sizes × eight attempts. All **80** runs converged and passed the recorded accepted-state physics checks, with fixed body/contact/island counts. **43 preflight CPU/unit tests passed**. The retained solver-source SHA-256 was `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24`; the previously rejected early-restart shader was not used.

**Independent signature checks:** Binary contact/state exports yield distinct hashes for canonical contact geometry, raw contact and root order, contact color assignment, unordered-within-color pass structure, colored stream, local index mapping, immutable free-state inputs, resulting FP64 state, arithmetic schedule and exact dispatch placement. The parser verifies complete contact coverage, prefix ranges, label consistency, and that contacts in one color touch disjoint bodies. Across each fixture's eight trials, the canonical contact set and free state were invariant. Wherever an arithmetic schedule occurred more than once, it produced the same iteration count and final FP64 work state. This is **an observed conditional result**, not a proof of determinism for schedules that never repeated.

| One connected island | Distinct color-pass signatures / 8 | Iteration range | Complete GPU tick range | GPU tick CV |
|---|---:|---:|---:|---:|
| Chain 16 | 1 | 452 | 2.55–2.57 ms | 0.18% |
| Chain 64 | 1 | 367 | 2.30–2.34 ms | 0.60% |
| Chain 256 | 5 | 4,035–4,036 | 32.37–37.98 ms | 6.93% |
| Chain 1,024 | 8 | 4,024–4,026 | 154.64–169.29 ms | 2.95% |
| Branching 64 | 1 | 321 | 2.79–2.80 ms | 0.11% |
| Branching 256 | 7 | 1,194–1,195 | 13.91–16.64 ms | 5.04% |
| Dense 64 | 4 | 107 | 1.79–2.06 ms | 4.81% |
| Dense 256 | 8 | 417–418 | 9.49–10.30 ms | 3.08% |
| Oblique/friction 64 | 3 | 265–309 | 4.71–5.46 ms | 6.39% |
| Oblique/friction 256 | 8 | 816–1,087 | 24.93–32.47 ms | 8.79% |

**Mechanism and bounds:** `physics.hlsl` scatters root contacts with atomic ranks; the greedy `ph_color` pass consumes the resulting order. `ph_members` also allocates local indices with atomic ranks. `ph_color_ranges` changes within-color placement via atomics. These are valid but schedule-dependent choices; the audit did **not** find missing or duplicate contacts. On chain-256, different orders led to **two versus three colors/batches** and an overall GPU-tick CV of **6.93%**. In the five attempts belonging to repeated equivalent-arithmetic cohorts, pooled within-cohort tick CV fell to **0.51%**. Chain-64 changed contact/stream order but held its color-pass schedule and 367 iterations.

Earlier traced records with identical binary and shader hashes confirm that chain-256 and chain-1,024 both restarted at **iteration 512** across the compared runs; color schedules and iteration counts nevertheless differed. Chain-64 did not restart. This restart comparison comes from **archived trace files**, not the new uninstrumented A/A timing runs; per-run restart counts were not measured in those 80 new runs.

**What cannot be inferred:** Every chain-1,024 trial had a distinct color/arithmetic and exact-dispatch schedule. Its **2.95% overall tick CV cannot be called GPU clock/runtime-only noise**; hardware-only variation at an identical schedule is **UNVERIFIED**. The same caution applies to same-iteration groups that change color work. GPU timestamps include upstream spatial work; no physical bandwidth, cache, GPU-clock, stall, or CPU submission attribution is proven.

**Impact on earlier quick-performance claims:** Independent recomputation of A/B medians from the 80 JSON runs yields identical-code **B/A ratios 0.8664725–1.1282261** across fixtures, geometric-mean ratio **0.9888429** and sum-of-p50 ratio **0.9955101**. Thus the previously used two-part aggregate retention rule can show an apparent gain of 1.12% by geometric mean and 0.45% by summed time **without any code difference**. Historical decisions remain documented as taken, but small changes, including the previous 0.28% broad geometric-mean win, are not established as reproducible speedups. These descriptive eight-sample results do not define a statistical significance threshold.

**Measurement-tool correction:** The initial exact-dispatch signature omitted contact-record placement. The analyzer was corrected and passed **seven focused tests**; it reprocessed the same 80 saved GPU exports, with **zero new GPU calls**. Old analysis is preserved in `results-before-dispatch-signature-fix.json` and the previous CSV. The corrected summary matches the 80 raw trials and has zero alerts. One handoff preservation-summary field still lists an older `measure_repeatability.py` hash (`52c21a5a...`), while the archived file and the final source-hash manifest both match `c4fb504149ef21d585e320da79cc5a7664462ebab3d76e8b8aa3b8917ef17643`. Keep the canonical final manifest and reconcile the stale summary when maintaining the tool.

**Decision: MEASUREMENT VARIATION CONFIRMED; NO SOLVER OPTIMIZATION.** This is not a demonstrated contact-coverage, KKT, synchronization or mathematical correctness defect. G5 remains **NOT QUALIFIED**. Production relaxation policy **1**, opt-in policy **4**, and retained solver defaults stay unchanged. No GPU code or runtime/shader binaries are committed in this documentation checkpoint.

**Next action:** Provide a **measurement-only deterministic contact/color schedule or exact-schedule replay** for matched controls, without enforcing its overhead on normal production execution. Prove stable geometry, contact coverage, color conflicts, FP64 execution order, convergence and rollback; measure sorting/replay cost separately from complete-tick time. Once equivalent arithmetic can be reproduced, revisit the hypothesis that reducing color passes improves the large-island solve. Do not tune restart thresholds against unmatched schedules.

**Evidence:** User-uploaded `G5-Measurement-Repeatability-20261019.zip`: preserved prior trace sets, `measure_repeatability.py`, `test_repeatability.py`, a local architecture excerpt, full 80-run JSON/CSV and raw contact/state exports, analysis correction history, 43-test preflight log and SHA-256 manifests. ZIP CRC test passed; JSON statuses, summary medians, A/B ratios and key source hashes were checked offline. The handoff reports that **388 original files and the working-tree status were preserved** in the original workspace. Recorded Windows GPU runs were not independently repeated here.

### G5 bounded deterministic measurement mode — PASS FOR MEASUREMENT ONLY (2026-10-19)

**Revision and scope:** Local, **unpublished** experiment commit `8c1777e1ddcc9fba15073565db62dfab79dc17c3`, branch `g5-deterministic-measurement-20261019`. The new `G5_DETERMINISTIC_MEASURE=1` HLSL path sorts complete contact records **together with their FP64 accumulated impulses** by stable key, rebuilds canonical member indices/root-contact ordering and per-color streams, and verifies a conflict-free schedule before solver execution. The existing greedy coloring and `projected_solver.hlsl` equations are unchanged. The bounded test mode accepts only **fixture 0**, flags **0/2**, at most **1,024 bodies**, **2,048 contacts**, **one connected island**, and **no contact graph expansion after the first round**. Unsupported cases fail before publication, with unchanged rollback. The sort is serial **O(C²)**; this is a correctness/measurement instrument, **not a proposed production scheduling algorithm**. The original workspace had all **390 checked file hashes and dirty status preserved**, per the handoff.

**Production isolation:** Normal shader compilation has `G5_DETERMINISTIC_MEASURE=0` and normal C execution has `G5_MEASURE_TIMESTAMPS=0`. The default-off C preprocessor token stream is byte-for-byte equivalent to the retained native source, and all four affected default-off DXIL shader outputs match the baseline hashes. Eight measurement timestamps fit inside the already reserved 64 query slots (40 normal slots); recorded brackets include dispatch/barriers/base bookkeeping, and no mid-pass CPU/GPU synchronization is added. The retained solver shader SHA-256 is `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24`. Production policy **1**, opt-in policy **4**, `G5_BODY_CACHE=0`, `G5_REUSE_MEASURE_BODIES=1`, and `G5_SKIP_OVERWRITTEN_RESIDUAL=1` stay unchanged.

**Windows recorded validation:** One serialized `python measure_deterministic.py` run on **NVIDIA GeForce RTX 4070 Ti SUPER** recorded **180 cold, one-tick GPU trials**: eight deterministic policy-4 runs per fixture (**80**), two ordinary native policy-4 controls per fixture (**20**), and two deterministic trials for each policy 0–3 per fixture (**80**). Of **160** deterministic trials, **150 converged**, and ten expected PGS/old-adaptive trials rejected with exact verified rollback. All **20** native policy-4 references converged. Two additional unsupported-envelope cases—**1,025 bodies** and **two islands**—returned error **64**, rejected without publication, and verified exact rollback. Initial **48 unit tests** and five focused post-setup-fix tests passed. Recorded verification covers independent contact coverage, single-island size, coloring conflicts, KKT, impulse reconstruction, energy/momentum and rollback.

**Independent audit:** ZIP CRC passes. All **1,513** archived file hashes match `manifest.json`, all **ten** JSON summary medians match the raw eight deterministic policy-4 trial timings and the saved CSV, and no accepted/rejected proof flag differs from the documented result. All deterministic fixture/policy combinations repeat identical **contact-set, contact-order, color assignment, per-color stream, local mapping, exact dispatch, FP64 work-state and published-state hashes**, together with constant solver iterations. This is an observed same-device/compiler bounded result, not a cross-device numerical determinism guarantee.

| Policy 4, connected island | Contacts | Solver iterations | Deterministic tick p50 | Scheduling bracket p50 | Native scheduling p50 | Tick CV |
|---|---:|---:|---:|---:|---:|---:|
| Chain 64 | 63 | 367 | 2.855 ms | 0.049 ms | 0.009 ms | 12.78% |
| Chain 256 | 255 | 4,035 | 36.246 ms | 2.985 ms | 0.011 ms | 1.74% |
| Chain 1,024 | 1,023 | 4,024 | 194.935 ms | **46.954 ms** | 0.017 ms | 2.11% |
| Branching 256 | 255 | 1,194 | 19.115 ms | 3.764 ms | 0.011 ms | 4.30% |
| Dense 256 | 480 | 417 | 19.715 ms | 9.182 ms | 0.011 ms | 18.57% |
| Oblique/friction 256 | 480 | 1,016 | 37.972 ms | 10.282 ms | 0.013 ms | 10.57% |

**Measurement limits:** Deterministic schedules do **not** make GPU execution time deterministic. On the 1,024-body chain, the **solver alone** spans **139.626–147.381 ms** despite an identical 4,024-iteration arithmetic schedule; its solver CV is **1.79%**. The complete GPU tick includes scheduling and timestamp instrumentation. The **46.954 ms** scheduling bracket is **not** a pure sorting-instruction cost, and a native run may solve with a different arithmetic schedule. The bounded serial sort is deliberately unsuitable for production or general larger/multi-island graphs. Eight cold samples are exploratory; no p99, thermal-stability, memory-stall attribution or cross-device result is established.

**Recovery/provenance:** Two setup-only failures (log-header comparison and pre-existing output directory) happened **before any GPU run**; preserved failure records are superseded by the successful `results.json`. The preceding repeatability archive's delivered helper `measure_repeatability.py` hashes to `c4fb504149ef21d585e320da79cc5a7664462ebab3d76e8b8aa3b8917ef17643`, matching its final manifest, while one supplemental summary incorrectly lists `52c21a5a...`. The helper hash at the **original previous GPU-execution time** remains **UNVERIFIED**. This deterministic batch recorded and verified its input/helper hashes before and after execution.

**Decision: RETAIN THE BOUNDED MEASUREMENT TOOL; DO NOT QUALIFY G5.** The original repeatability blocker is resolved **inside the declared envelope**. It does not demonstrate a faster general engine, strict immutable state-buffer publication, GPU-02 displayed FPS, sustained simulation, or a production-ready canonical scheduler. **No solver or runtime code is pushed** to GitHub by this documentation-only update.

**Next action:** Use the fixed-schedule measurement control to study one actual large-island **FP64 solver/color-pass work reduction** while reporting solver-only timings, iteration counts, matched correctness and exact arithmetic signatures. Separate deterministic schedule-building overhead from execution, avoid applying the serial O(C²) sorter to production, and stop if new arithmetic schedules or insufficient repeatability make a small claimed speedup inconclusive.

**Evidence:** User-uploaded `G5-Deterministic-Measurements-20261019.zip` with `source/`, `reference/`, `changes.patch`, `evidence/current-batch/results.json`, `summary.csv`, full raw exports, two explicit rejection proofs, output/shader hashes, test logs, and prior-handoff hash reconciliation. The GPU run occurred on the recorded Windows machine and was **not independently rerun** for this documentation review.

### G5 post-color device-barrier coalescing — REJECT (2026-10-19)

**Experiment and source:** Local branch `g5-color-boundary-measurement-20261019`, revision `960722f7351d691f8d33b2ef627365d8c1a9d01b`. An opt-in compile flag `G5_COALESCE_COLOR_BARRIER=1` omitted the **outer** `DeviceMemoryBarrierWithGroupSync()` after a complete color pass and after mandatory reconstruction, **only for a nonempty global-memory island**. The final nonempty color's final batch already uses a device/group barrier in `applyColor()`. Local-storage islands (`localMode==1`) and zero-color islands kept the outer device barrier. The intent was to avoid **two redundant outer device/group barriers per solver iteration** without changing the final color's existing device/group synchronization. The patch changes the barrier boundary around the loop, not the FP64 contact equations, normal/tangent projection, KKT scan, iteration budget or relaxation/restart logic.

**Existing baseline:** The retained source is still SHA-256 `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24`, and the exact tested candidate source is `f78f5a2232e0808d3aba58ab0e91e929a29410ee7b1c98f2200a4104effb2f2d`. Candidate and control variants were built for all policies 0–4, with `G5_BODY_CACHE=0`, `G5_REUSE_MEASURE_BODIES=1`, `G5_SKIP_OVERWRITTEN_RESIDUAL=1`, and the previously rejected `G5_EARLY_RESIDUAL_RESTART=0`. Test-only canonical contact scheduling remained on; ordinary default production policy is still 1 with deterministic measurement off. Disassembled candidate and control policy-4 `ph_solve` contain **20 static barrier instruction sites** each: the change alters which branch executes a barrier, not the static DXIL site count. Static/source-derived execution counts are **not** measured GPU stall or cache counters.

**Recorded headless test:** One serialized Windows CLI batch on **NVIDIA GeForce RTX 4070 Ti SUPER** ran **240 single-tick trials**: eight *paired* control/candidate policy-4 samples for each of ten frozen fixtures (**160** runs), plus one matched pair for each of four other solver policies per fixture (**80** runs). Per arm, **115 converged** and **five expected PGS/original-adaptive attempts rejected**. All **230 accepted** trial records passed independent invariant audits; all **ten rejected** trial records verified rollback. Each paired policy/fixture preserved the exact contact set, colored stream, arithmetic schedule, iteration count, FP64 work/impulse values and final published-state signature. The recorded preflight had **46 passing unit checks**; after restoring the baseline, **49 unit tests passed**. The targeted test intended to reject the pre-change source also failed as expected before the candidate patch, and that log is retained. No GPU run was performed during this documentation update.

| Deterministic policy-4 fixture | Solver p50 control → candidate | Complete tick p50 control → candidate | Iterations |
|---|---:|---:|---:|
| Chain 64 | 2.322 → 2.104 ms | 3.264 → 3.268 ms | 367 |
| Chain 256 | 32.021 → 32.117 ms | 35.689 → 35.195 ms | 4,035 |
| **Chain 1,024** | **147.503 → 143.696 ms** | **193.720 → 191.815 ms** | **4,024** |
| Dense 256 | 6.819 → 7.053 ms | 20.619 → 17.036 ms | 417 |
| Oblique/friction 256 | 25.328 → 25.323 ms | 36.261 → 40.172 ms | 1,016 |

**Predeclared retention test:** The 1,024-body policy-4 *solver-stage paired geometric* ratio is **0.98847**, with 95% paired-bootstrap interval **[0.97077, 1.00718]**. The medians above give a nominal 2.6% solver-stage improvement, but the same-batch control A/A p95 deviation/noise floor is **4.3576%** and the interval includes no improvement. The required gain `>max(3.6%, A/A noise floor)` was **not met**. Across all ten policy-4 fixtures, the equal-fixture complete-GPU-tick aggregate ratio is **0.9981204** with 95% interval **[0.9717317, 1.0254798]**; the aggregate interval is not fully below 1, so the second performance gate **also fails**. Complete-tick changes include ~45 ms of test-only deterministic scheduling on the 1,024-body chain, and its scheduling bracket is not an independent sorting-only hardware cost. Eight paired cold samples per policy-4 fixture support only this limited noisy comparison—not stable p99, sustained simulation, or a universal speedup.

**Independent archive checks:** Uploaded `G5-Deterministic-Solver-Work-20261019.zip` contains **1,985 ZIP members** (including `manifest.json`) and **1,984** per-file SHA-256 entries; all matched. ZIP CRC passed. All ten summary rows' recorded control/candidate GPU-tick and solver medians were recalculated from the corresponding eight raw runs and matched. The manifest, source diff and `restoration.json` identify the correct retained-versus-executed shader copies. Compiled binaries and build caches are not included, so this is evidence of a recorded Windows test, not independently rerun GPU qualification.

**Decision: REJECT AND RESTORE.** The candidate is correct in the recorded deterministic measurement envelope but cannot meet the predeclared noise-aware performance criteria. The archive confirms the active retained shader was restored byte-for-byte to SHA-256 `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24`. Neither the original working tree nor the production solver's settings changed; G5 remains **NOT QUALIFIED**, GPU-02 displayed-frame validation remains unverified, and G6 is unauthorized. **No experimental solver source is committed to GitHub** by this documentation checkpoint.

**Next action:** Stop barrier coalescing experiments. Inspect repeated *contact-local FP64 body loads* in `applyColor()` while preserving the updated normal-impulse state used for subsequent tangential projection. Make one narrowly justified correctness-first change only if data dependencies permit it. Use identical deterministic contact schedules, a matched paired control and candidate, and a noise-aware full-tick/solver criterion in one bounded headless batch. Reject if the change is not clearly measurable or changes exact FP64 acceptance/rollback.

### G5 contact-local FP64 body snapshot reuse — REJECT (2026-10-19)

**Hypothesis and source:** A new, opt-in HLSL `G5_CONTACT_SNAPSHOT=1` path loads both bodies once per contact into lane-private `Body` structures instead of repeatedly calling `relative()` and `delta()` in the normal and tangential impulse phases. In `applySnapshotContact()`, the normal impulse is projected and applied first; `deltaSnapshot()` mutates the same local `Body a/b` values **and preserves the original ordered body stores and wake operations**, then the tangent impulse reads that **updated** local state and uses the same Coulomb constraint. Conflict-free contact colors ensure no other lane writes either body during that color. Rebuild, other color passes, FP64 arithmetic, contact equations, barriers, KKT acceptance, energy/momentum bounds, solver policies, rollback and iteration/work caps are unchanged. The previously rejected early-restart and post-color-barrier modifications were **not** reapplied.

**Compile-mode and SHA evidence:** The experimental macro defaults **off** (`G5_CONTACT_SNAPSHOT=0`) and was toggled through separately compiled candidate/control policy 0–4 shaders. The exact tested candidate `projected_solver.hlsl` has SHA-256 `49067a3ed2cc01fad8c0a5ef77ae8b97a1a2dbe0748736a6a3334dbd6e2d66d3`. The exact retained/current solver and archived unchanged control both match SHA-256 `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24` byte-for-byte. Static disassembly of policy-4 `ph_solve` reports **191 → 160** buffer-load **instruction sites**; **153 FP64 arithmetic sites** and **20 barrier sites** remain unchanged. These site counts are **not** measured physical GPU memory transactions, bandwidth, occupancy, or execution stalls. The source uses legacy `bufferLoad`; `rawBufferLoad` zero counts in the preliminary DXIL script do **not** mean the shader performs no reads.

**Matched Windows headless evidence:** An isolated Windows GPU batch ran **240 cold one-tick trials**: eight matched, AB/BA policy-4 control/candidate pairs for each of ten frozen chain/branching/dense/oblique fixtures (**160** trials) plus one control/candidate pair per fixture for each of policies 0–3 (**80** trials). Recorded GPU: NVIDIA GeForce RTX 4070 Ti SUPER. **Per arm, 115 converged and five expected PGS/original-adaptive cases rejected.** All **230** accepted trials verified the invariant/KKT/impulse reconstruction/energy/momentum checks, while all **ten** rejected trials verified exact rollback; no timeouts or runtime errors were reported. All 50 policy/fixture comparisons have **identical** contact/color/arithmetic/dispatch schedules, iterations, FP64 work-state, contact impulses and accepted published-state hashes. All **ten** summary rows' medians were independently recomputed from underlying timing runs, with no mismatches. Recorded preflight: **46 passing tests**; post-restoration baseline: **49 passing tests**. These are related test suites, not 95 independent coverage areas. Windows GPU execution was **not independently rerun** by this documentation reviewer.

| Policy-4 deterministic fixture | Solver GPU p50 control → candidate | Complete GPU tick p50 control → candidate | Iterations |
|---|---:|---:|---:|
| Chain, 16 bodies | 2.742 → 2.502 ms | 3.150 → 2.919 ms | 452 |
| Chain, 64 bodies | 2.224 → 2.304 ms | 3.135 → 3.001 ms | 367 |
| Chain, 256 bodies | 32.037 → 31.550 ms | 35.633 → 35.120 ms | 4,035 |
| **Chain, 1,024 bodies** | **142.926 → 138.685 ms** | **192.734 → 189.745 ms** | **4,024** |
| Oblique/friction, 256 bodies | 25.352 → 24.354 ms | 38.907 → 33.531 ms | 1,016 |

**Uncertainty-aware decision:** The chain-1,024 paired geometric solver ratio is **0.97490945** (nominal 2.51% gain by paired ratio, versus 2.97% reduction in unpaired medians), with paired-bootstrap 95% interval **[0.94898109, 1.00295631]**. The same-batch control A/A p95 deviation/noise floor is **5.3183%**, greater than both the nominal and paired gains and the historical 4.3576% minimum. The primary predeclared rule requires the solver gain to exceed the larger floor **and** the 95% paired interval to be wholly below 1: **FAIL**. Across ten policy-4 fixtures, the geometric aggregate complete-tick ratio is **0.96623219**, 95% interval **[0.93714076, 0.99502117]**, which **passes the separate aggregate criterion**. The primary failure vetoes retention. The test-only deterministic schedule bracket on chain-1,024 was **45.850 → 46.994 ms**, and CPU record+submit median **3.505 → 3.516 ms**. Eight cold matched samples per fixture do not establish p99, sustained simulation speed, or cross-device reproducibility.

**Source integrity and GitHub history:** The user's `G5-FP64-Body-Loads-20261019.zip` passes ZIP CRC; **all 1,986 manifest-listed file SHA-256 hashes** match the archived bytes. The isolated experiment branch `g5-contact-snapshot-20261019` was already pushed to GitHub by the Windows Codex run at revision `fa4a11914879455cada2115e50d38d6936ab753a`; its architecture file is a local branch-specific report, **not** a replacement for the complete continuously updated `main`/playable records. The rejected candidate patch is archived on that branch but is **not merged** into the production branch. The archive reports original-workspace preservation for **394 checked files and unchanged working-tree status**. Its active retained shader and source hashes are verified offline here; there is no claim of a live Windows rebuild.

**Decision: REJECT / EXACT RESTORATION.** The contact-local snapshot is a correctness-preserving optimization **in the tested bounded deterministic envelope**, but its key 1,024-body solver gain cannot be distinguished from the measured A/A variation at the predefined threshold. The original solver source was restored byte-for-byte. Retain existing local `G5_REUSE_MEASURE_BODIES=1` and `G5_SKIP_OVERWRITTEN_RESIDUAL=1`; keep `G5_BODY_CACHE=0`, production relaxation policy **1**, opt-in policy **4**, and test-only deterministic scheduling **off** by default. G5 remains **NOT QUALIFIED**; G6 unauthorized and GPU-02 displayed FPS unverified.

**Next action:** Stop isolated low-single-digit load/barrier micro-optimizations. Use deterministic contact schedules to analyze the roughly **4,024 required iterations** on the 1,024-body connected chain: residual contraction, color-pass count and convergence bottleneck. Produce a source/trace-backed choice of **one topology-independent algorithmic approach** to reduce required solver work, with a carefully defined correctness contract, and test it against matched native/control builds only after the hypothesis is justified. Keep the serial deterministic scheduler measurement-only and account for its overhead separately. Do not weaken KKT, energy/momentum, rollback, or contact coverage.

**Evidence:** `G5-FP64-Body-Loads-20261019.zip`: `README.txt`, `manifest.json`, retained/experimental HLSL sources and patch, `evidence/results.json`, `summary.csv`, complete 240-trial exports, DXIL analysis, build/test logs, restoration checks, and GitHub push/verification logs. Results reflect one recorded serialized Windows GPU batch; they are **not** GitHub CI or an independently rerun qualification.

### G5 bounded Anderson convergence experiment — REJECT / CURRENT SPRINT CLOSED (2026-10-19)

**Cause analysis:** The tested 1,024-body collinear, unit-inverse-mass chain has 1,023 adjacent normal constraints. Its settled linearized normal operator is `tridiag(-1,2,-1)`, with condition number approximately **424,971**. The measured post-restart residual envelope for deterministic policy 4 decays by about **0.99500435 per sweep**, consistent with the retained fixed-SOR damping near 0.995; the control requires **4,024 sweeps** (512 adaptive plus ~3,512 fixed-SOR). This is a **fixture-specific linearized explanation**, not proof that frictional contact networks with changing active sets follow the same operator. Optimizing FP64 loads, residual scans or barriers alone cannot remove this long-range coupling.

**Tested change:** An opt-in, depth-one safeguarded Anderson extrapolation on the existing eight-sweep impulse map. The trial limits acceleration coefficients, projects impulses, requires a reconstructed KKT check, restores checkpoints on rejected attempts, resets history, and charges scans/trials against the **existing** work cap. The implementation uses checked, arena-backed scratch of **48 bytes/contact**, up to **64** trials, no new scheduler or GPU allocation. Sleeping/insufficient-capacity fallback source guards were **not** separately GPU-qualified. This is an algorithmic candidate, not a new default.

**Recorded Windows evidence:** `G5-Algorithmic-Convergence-20261019.zip` from local revision `a147f6bf265bc82060107358cd41157e38d371c2` on pushed **evidence branch** `g5-convergence-anderson-20261019`. The archive passed ZIP CRC and all **2,159** listed SHA-256 checks. It contains **240 serialized one-tick GPU trials** (ten existing fixtures × policies 0–4 × matched control/candidate; eight samples/arm for policy 4 and one sample/arm for each other policy) plus **20** deterministic residual probes. The independent acceptance and rollback flags were recorded; the control had **115 accepted / five expected rejected**, while the candidate had **93 accepted / 27 rejected**. Its **22 extra rejected trials** represent **eight distinct previously converging topology/policy configurations**, not 22 unrelated configurations. All rejected attempts verified rollback; all accepted attempts passed the recorded invariant audits. Baseline preflight **46** and restored-baseline **49** unit tests passed. The Windows GPU commands were not rerun during this documentation review.

| Policy-4 deterministic fixture | Baseline sweeps | Candidate sweeps | Candidate outcome |
|---|---:|---:|---|
| Chain 16 | 452 | 65 | Accepted |
| Chain 64 | 367 | 664 | Accepted, more work |
| Chain 256 | 4,035 | 3,397 | **REJECTED** |
| Chain 1,024 | 4,024 | 3,445 | **REJECTED** |
| Branching 256 | 1,194 | 357 | Accepted |
| Dense 256 | 417 | 64 | Accepted |
| Oblique/friction 256 | 1,016 | 235 | Accepted |

The two hard-chain rejected cases spent another ~699/651 units of charged trial work, respectively. On chain-1,024, reconstructed terminal KKT ratio increased **0.9830 → 107.98**. The nominal policy-4 solver/tick timing **143.393/193.555 → 130.096/178.800 ms** belongs to a **rejected attempt**, cannot be reported as simulation acceleration, and must not be counted as a qualified performance gain. Attempted-tick aggregate statistics likewise include rejected runs and are **not valid qualified throughput comparisons**. The candidate loses convergence for chain-64 policies 1 and 3, chain-256 policies 1/3/4 and chain-1,024 policies 1/3/4.

**Decision: REJECT AND RESTORE.** The tested `projected_solver.hlsl` SHA-256 is `53e7957940c76790a4d00b943b1c05c6acd662ebe0445858e3e7f70bb93bae7e`; the exact retained shader SHA-256 is `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24`. The handoff's preservation record reports the latter restored byte-for-byte, with production relaxation **policy 1**, prior retained local snapshot-reuse/skip-overwritten-residual logic, body cache off and test-only deterministic scheduler off by default. The experimental branch was pushed but not merged into `main` or the playable branch. G5 did **not** pass its large-island convergence or performance gate.

**Project-level disposition — CLOSE THE CURRENT G5 WORKSTREAM AS DEFERRED, NOT PASSED:** Stop repeated G5 micro-optimization and acceleration experiments. Preserve the baseline, the rejected-candidate evidence, the quick fixture/correctness tests, and the risk description. Mark G5 **DEFERRED / NOT QUALIFIED** in the gate table. This is an explicit scheduling/priority decision, **not** a technical pass, a waiver of the large-island limitation, a full-engine release approval, or evidence of sustained 1,024-body real-time physics.

**Proceed independently where safe:** Work may continue on resource planning, state isolation, scheduler/host interfaces, smaller/scattered-island workloads, error handling and headless coverage **without claiming that G5-dependent acceptance criteria are satisfied**. G6 **preparation and scope definition** are permitted, but **formal G6 foundation approval remains unauthorized** until its relevant technical gates pass or an explicit, separately approved scope/risk-acceptance decision is documented.

**Reopen G5 only when:** (a) a representative application scenario actually requires the large-connected-island target, or (b) an evidence-backed architecture change offers a material improvement worth a dedicated prototype; set explicit target latency/throughput and acceptable failure handling first. Explore multilevel/global low-mode correction, a domain-decomposed or parallel solver, or an alternative constraint formulation **as separate proposals**, not as automatic follow-on benchmark loops. Preserve correctness, KKT, rollback, multi-island generality and full-tick cost accounting.

### G6-P1 immutable consumer-state publication — LOCAL PREPARATION PASS (2026-10-19)

**Implementation / provenance:** User-supplied `G6-P1-State-Isolation-20261019.zip`, local implementation revision `603fd67506ede889bf6c7bc4b9cd034183d97ccb`, branch [`g6-p1-state-isolation-20261019`](https://github.com/Cryosimorgh/GPU-physics-engine/tree/g6-p1-state-isolation-20261019), base `a147f6bf265bc82060107358cd41157e38d371c2`. New `state-publication.h/.inc`, `publication-runtime.inc`, and bounded changes to physics/runtime/viewer/CLI tests. The experiment **is committed on a separate branch**, not merged to `main` or the playable branch. The original working tree and its three dirty compiled artifacts remain unchanged according to the handoff receipts. **G5 remains DEFERRED / NOT QUALIFIED; G6 formal approval remains NOT QUALIFIED.**

**State lifecycle and invariants:**

1. The legacy G1 source/identity buffers are **producer-private borrows**, not stable immutable consumer leases. The existing trial, discovery, contact, solver, GPU guards, and `ph_publish` path continue to run in their original sequence. After publication, a GPU copy captures 64 bytes/capacity body components, a 256-byte header, 12 bytes/capacity identity maps, and, for fixture 13, 160 bytes of persistent pool material/rolling state into a **separate immutable GPU buffer**. No trial scratch is exposed.
2. The writer selects a free publication slot that is neither currently accepted, reader-pinned, pending, nor fence-incomplete. GPU copies and transitions to COMMON are ordered in the compute queue, then fenced. The CPU marks the new slot accepted only after the terminal GPU fence and completed-frame acceptance header agree on error state, tick, epoch and body count. Rejected solver states do not displace the last accepted snapshot. Failed completion poisons the Physics instance rather than silently publishing.
3. Every consumer obtains a read-only `PhStateLease` carrying runtime/context identity, nonwrapping publication serial, unique nonce, generation, tick/epoch, buffer and readiness fence. A 64-entry table checks the exact handle and refuses stale/forged/double releases. Any asynchronous GPU consumer must register **its completion fence before submitting commands**; the lease cannot release until that fence signals. A CPU-only holder may release after CPU use; raw legacy source handles are never permanent GPU leases. The owner-thread API is **serialized**, not a thread-safe concurrent host interface.
4. Two slots are pre-admitted by default; explicit reserve allows up to four. If no slot is free, the candidate returns bounded **error 60** *before* advancing the simulation tick or overwriting accepted state. No implicit eviction or allocation during normal ticks. Destroying Physics with live leases is refused; closing Storage with live Physics owners is refused. Structural mutation requires drained producer work and no live leases. Runtime identity and fence ownership checks block stale contexts and foreign-device use.
5. Injected GPU command-recording failure restores resource-state bookkeeping and discards an unsubmitted packet; previously submitted split packets retain their fence ownership. This is **not** a demonstrated physical dispatch/device-loss recovery. Native D3D12 `ID3D12Device` objects were **shared** between test runtime instances despite distinct StorageDevice identities; cross-physical-device cases remain untested.
6. Existing viewer legacy source reading retains same-queue graphics/compute synchronization and fenced per-frame copies; the candidate viewer source was **compiled but not launched**. No networking consumer is currently implemented. The lease mechanism is not proof that all future consumers are correctly integrated.

**Verification:** One final serialized Windows `python run_g6_p1.py` batch recorded **21/21 PASS processes**, including publication, regression (idle, collisions, energy, discovery, ownership), device identity, recycling/delete, and twelve AB/BA workload timing processes. GPU errors reported by the final tests: **zero D3D12 validation errors**. The handoff also archives earlier preflight/fence-harness failures separately; they are not counted as passing results. The supplied ZIP passed CRC and all **422 manifest-listed SHA-256 file checks**. Candidate/source artifacts in the uploaded ZIP match the separately pushed implementation branch. Shader sources and **all candidate/control DXIL shader outputs** are recorded unchanged, including the retained `projected_solver.hlsl` SHA-256 `10c5ee6541c7799119a9578b304c51f8d3de3938e2221613894bc7fae75d5c24`. This is **recorded Windows GPU evidence, not independently rerun testing or GitHub CI**.

**Bounded overhead:** Each committed immutable publication slot reserves `76*C + 256 + (fixture13 ? 160 : 0)` logical bytes, aligned using the D3D12 allocation info. At capacity **C=32**, two default slots add **131,072 bytes (128 KiB)** of committed GPU allocation, with **zero normal-tick slot allocations**, **zero additional CPU uploads**, and **zero additional per-tick GPU-to-CPU readback bytes**. The per-tick GPU copies of accepted state are **not zero**; they are approximately `76*C + 256` bytes plus the optional 160 bytes for pool state. For an idle workload, the logged 64 warm samples per arm (two 32-sample AB/BA repeat blocks) give total GPU tick **p50 262 → 263.75 μs**, **p95 265 → 267 μs**, and CPU record + queue-submit p50 **212.5 → 213.5 μs**. The publication-tail reported median is **3 → 5 μs**. Moving p50 remains approximately **398 → 398.5 μs**. No sustained, p99, heterogeneous workload, or broad throughput guarantee is established.

**Timing accounting caution:** The reported `break` p50 (control **856 μs**, candidate **761 μs**) does not agree with a direct recomputation of pooled 64 raw trials using the *last* exported `gpu_cumulative_us` timestamp (approximately **863.5 μs** control, **808.25 μs** candidate). The CLI's reported timing definition and last cumulative timestamp may differ, but the archive does not establish the reason. **Do not use this discrepancy to claim a solver speedup** or a reliable break-case gain; reconcile timestamp accounting before a performance gate.

**Disposition: RETAIN AS G6-P1 LOCAL PREPARATION PASS, NOT G6 GATE QUALIFICATION.** Immutable accepted generations now have a bounded, explicitly fenced consumer API within the tested owner-thread contract. However, real hardware dispatch failure, physical device removal/recovery, true cross-native-device safety, full viewer lifecycle, consumer API integration outside the tests, and sustained execution remain **UNVERIFIED**. Do not promote this branch as an approved engine foundation, and do not reactivate G5.

**Next action:** Establish a small, bounded G6-P2 resource/scheduler and consumer-integration contract around the new lease API: explicit resource admission and ownership, per-queue completion handoff, backpressure, error propagation, and a headless real consumer scenario. Start with an audit; avoid a wholesale scheduler rewrite. Track the distinct native-device/unverified device-loss boundary. Keep graphical or network integration claims unqualified without actual end-to-end evidence.

### G6-P2 resource ownership and bounded task dependencies — LOCAL PREPARATION PASS (2026-10-19)

**Scope and implementation:** The user-uploaded `G6-P2-Resource-Ownership-20261019.zip` contains an isolated Windows implementation at revision `7fdd05e38acfe04c264997f880a665f48affe799`, branch [`g6-p2-resource-ownership-20261019`](https://github.com/Cryosimorgh/GPU-physics-engine/tree/g6-p2-resource-ownership-20261019), based on G6-P1 revision `603fd67506ede889bf6c7bc4b9cd034183d97ccb`. The branch is **not merged** into `main` or `billiards-playable-requalification-20261018`. New `work-ownership.h/.inc`, `resource-claims.inc`, headless ownership tests and bounded updates to the P1 physics/runtime/publication interfaces implement **resource admission and completion tracking on existing D3D12 queues and snapshot leases**. There is **no new general-purpose task scheduler**, solver modification, normal-tick GPU allocation, or added per-tick CPU readback/wait.

**Resource and task contract:** Each consumer task owns a P1 immutable accepted-state read lease plus **at most three additional resources**, declared with exclusive-write/shared-read access. The resource ledger checks buffer validity, retirement/transition conflict, outstanding writer/reader claims, and external resource availability; partially acquired claims unwind on admission failure. Producer work exposes up to **32 explicit resource dependencies** with queue/fence and publication-generation provenance. A fixed **64-entry lease/task table** admits requests without hidden task eviction or new GPU allocations. The CPU API is **owner-thread serialized**, not a general concurrent host scheduler. Both producer and consumer work retain resource claims/immutable state until their respective recorded completion fences allow safe release. Buffer retirement and conflicting state changes are blocked while claimed.

**Submission and cancellation:** Consumer submission retains a queue only when it belongs to the expected native D3D12 device, validates the future external completion fence and registers it **before externally submitted work**. A duplicate, already signaled, or foreign-device fence cannot silently acquire ownership. Pre-submit cancellation/failure releases claims immediately. After submission, `cancel` and `fail` mark work pending and **do not preempt GPU commands** or release the consumer snapshot/output until the completion fence signals. Stale task handles and cross-context references fail. Producer failure preserves existing published generations and consumer ownership. No assumption is made that this protects arbitrary shaders which bypass the declared resource dependencies.

**Final headless evidence:** A serialized `python run_g6_p2.py` Windows batch recorded **22/22 PASS process runs**, all return codes zero, on the existing device/driver with **zero reported D3D12 debug validation errors**. Coverage includes read/write resource conflicts, shared readers, immutable snapshot write rejection, native copy-queue consumer overlap, delayed consumer fences, pre- and post-submit cancellation, queued failure cleanup, slot/task exhaustion, claim rollback, stale/context handles, producer failure, ordinary physics regressions, memory and timing scripts. The test suite covers **one producer and bounded GPU consumers**, not arbitrary multi-device producers, custom untrusted shader access, or a real application/network consumer. The viewer was **compiled successfully but not launched**. The failed initial attempt used the wrong memory-probe warmup setting; `initial-attempt/` keeps that history, and the corrected **final** evidence is in `evidence/g6-p2/results.json`.

**Audit and source integrity:** The archive's CRC is valid, and all **252** `manifest.json` file SHA-256 entries match the ZIP contents. The uploaded handoff's `changes/` source snapshots match their manifest source hashes, and the core `work-ownership.inc`, `resource-claims.inc`, and `runtime.c` are available on the pushed isolated branch. The final `gate-G6-P2.json` states G5 remains deferred and G6 unqualified; all baseline and candidate DXIL shader hashes match, including unchanged `projected_solver.hlsl` and `physics.hlsl`. Original P1 workspace preservation of **327 tracked file hashes** and the four pre-existing dirty build outputs is reported by the local Windows handoff, not independently established on the remote machine. This review checked local archive records; it did **not** rerun Windows GPU execution.

| Measured headless fixture (64 warm samples per arm; two repeated AB/BA blocks) | P1 control | G6-P2 candidate |
|---|---:|---:|
| Idle complete GPU tick p50 / p95 | 266.75 / 269 μs | 266.5 / 269.5 μs |
| Moving-contact GPU tick p50 / p95 | 406.75 / 408.5 μs | 406.75 / 409.75 μs |
| Idle CPU record + submit p50 | 217.5 μs | 213.6 μs |
| Moving CPU record + submit p50 | 240.1 μs | 242.7 μs |
| GPU allocations | 23 | 23 |
| GPU committed bytes | 1,507,328 | 1,507,328 |

**Performance interpretation:** These bounded comparisons show no material added GPU memory or complete-tick time in the tested 32-body workflows; they **do not** demonstrate a throughput improvement, device-loss recovery, or sustained tail latency. No added GPU allocations/committed memory were observed even on task exhaustion. The third `break` workload is explicitly **excluded** from performance conclusions: `p1-break-audit.json` reproduces historical printed quantiles from the raw samples, and the new batch satisfies timestamp ordering, but an unexplained approximately **95 μs** execution-time mode shift remains. This is an attribution problem, not evidence of failed ownership correctness.

**Decision: RETAIN P2 ON THE ISOLATED DEVELOPMENT BRANCH; FORMAL G6 NOT QUALIFIED.** Safe bounded task/resource ownership has passed the recorded local envelope. The work is **not** proof of physical device removal/recovery, arbitrary user-written shader resource safety, multi-producer/multi-device scheduling, live viewer/network integration, formal GPU-02 displayed FPS, or universal engine foundation readiness. G5 stays **DEFERRED / NOT QUALIFIED**, and G6 may continue independent preparation without waiving those gates.

**Next action:** In G6-P3, integrate one **real native application consumer** of accepted GPU snapshots (the existing renderer is preferred), using the P1/P2 lease/task contract with explicit producer→consumer queue wait and registered completion fence, and verify its lifecycle through a bounded headless run. Make device-loss/teardown behavior explicit and test supported failure paths, but do **not** claim real physical device-loss recovery unless an actual removal/recreation test completes. Do not create a new scheduler or reopen G5.

### G6-P3 real application GPU renderer consumer — LOCAL PREPARATION PASS (2026-10-19)

**Implementation and provenance:** User-supplied `G6-P3-Real-Consumer-20261019.zip`, experiment revision `621f6d626cabd2ccf187db695b658f99a80c9586` on branch [`g6-p3-real-consumer-20261019`](https://github.com/Cryosimorgh/GPU-physics-engine/tree/g6-p3-real-consumer-20261019), based on G6-P2 `7fdd05e38acfe04c264997f880a665f48affe799`. `viewer.c`, `render-consumer.inc`, `state-publication.inc`, `work-ownership.inc/.h`, `render-consumer-tests.inc`, HLSL renderer/layout and pool snapshot schema were updated. The implementation is committed **only on the isolated branch**; the authoritative `main` and playable branches contain this documentation decision, **not** the P3 production source integration. G5 remains **DEFERRED / NOT QUALIFIED** and formal G6 approval remains **NOT QUALIFIED**.

**Actual application consumer:** The existing viewer `vrender()` and its real D3D12 pipeline states, resource bindings and `DrawInstanced` calls now use a G6-P1 immutable **accepted** state snapshot through G6-P2 `PhWorkHandle` dependency admission. The consumer acquires and pins an accepted generation, records bounded read/write dependencies, registers its graphics queue and future completion fence **before** external GPU execution, explicitly inserts `ID3D12CommandQueue_Wait` on the producer readiness fence, renders from leased state/body/map/header/persistent pool fields, and holds the lease/resources until graphics-fence completion. Delayed readers, cancellation and failure remain bounded; rejected unpublished generations cannot replace the last accepted one. The legacy fenced private-source copy route is kept only as a **matched test control**; normal intended renderer path is the lease-driven consumer.

**Correctness and scope:** The functional `render_consumer.exe --profile 13 --samples 0` invokes the actual application renderer and shows **495 pipeline vertex invocations**, nonzero pixel-shader activity, and **16 rendered instances per frame** with real D3D12 commands. Headless proof includes two-queue producer/consumer overlap, a blocked graphics fence, safe snapshot reuse, stale/failed task cleanup, bounded backpressure, poison of producer-private buffers while the accepted immutable generation remains readable, attempted rejected-tick withholding, pool snapshot bounds and pick/verification metadata. Pool-status source and snapshot offsets were corrected together; all **32 physics DXIL** control/candidate pairs are **byte-identical** and no solver mathematics, KKT limit, fixed timestep or production relaxation policy changed. This is **offscreen functional evidence**, not visual pixel-image correctness or live interactive presentation: no HWND, swap chain `Present`, screenshot/pixel readback or physical device-loss test ran. A synthetic rejected state and injected recording failure do not establish true device-removal recovery.

**Recorded test evidence:** The final one-batch Windows `python run_g6_p3.py` evidence lists **14/14 PASS serialized process runs**, including real renderer consumer, G6-P1/P2 publication and ownership regression tests, pool idle/contact/energy/discovery tests, paired 16-sample/arm render timing in each of two AB/BA blocks, and independent 32-body memory/control tests. The functional scenario enables D3D12 debug validation and records zero errors in related physics/publication/ownership checks; recorded per-render timing processes do not enable validation. The original workspace's **333 tracked file hashes and dirty status were reported unchanged**. ZIP CRC and **all 877** manifest-listed SHA-256 hashes were verified; changed source snapshots were checked against the source manifest. The pushed branch contains the new renderer integration. Windows GPU execution was **not independently rerun** in this review.

| Offscreen P2/control vs P3/candidate (32 samples/arm) | Control | Candidate |
|---|---:|---:|
| Graphics GPU render p50 / p95 | 18.432 / 18.848 μs | 18.432 / 19.456 μs |
| CPU record + submit p50 / p95 | 434.5 / 471.3 μs | 450.9 / 799.6 μs |
| CPU blocking acceptance wait p50 / p95 | 0 / 0.100 μs | **1,131.8 / 2,026.2 μs** |
| Complete GPU tick p50 / p95 | 1,259 / 1,690 μs | 1,174 / 1,870.25 μs |
| Offscreen total committed GPU allocation | 2,883,584 bytes | 2,686,976 bytes |
| Offscreen GPU allocation count | 42 | 39 |

**Performance interpretation:** Published p50 values use the **lower middle sample** of the 32 sorted samples, not the arithmetic average of the middle pair; this convention reproduces every reported CSV p50. The paired `control` adapter and `candidate` run the same real viewer rendering pipelines in offscreen mode but are **not byte-identical interactive runtime builds**; no throughput or frame-rate speedup is proven. Render GPU time remains about **18.4 μs**; memory is **196,608 bytes (192 KiB)** and **three allocations** lower in this specific offscreen comparison. The mandatory CPU-side accepted-state decode/check currently calls `gp_wait` before renderer submission and introduces a material **~1.13 ms median blocking wait**; it can limit overlap even though the graphics queue also has a GPU readiness wait. The full-tick p95 worsens and the timing sample distribution is wide. Avoid treating smaller p50 tick as an engine-performance gain. The previous P2 `break` fixture's unexplained ~95 μs time-mode discrepancy remains separate and unresolved.

**Resource contract correction needed:** P3 increases `PH_WORK_EXTRA` from **three to five** to cover actual renderer diagnostic/readback/timestamp/HUD/capture dependencies. The bounded CPU-owner-thread API still has 64 lease/task entries and 32 producer dependencies. The public `work-ownership.h` comment still says "*at most three separately owned resources*" and is **stale**; align it with the actual verified bound before any public API guarantee. The headless combination of capture plus pipeline stats is not admitted if it exceeds five extras, by design. This is not evidence of a general-purpose resource scheduler or arbitrary external-shader safety.

**Decision: RETAIN G6-P3 AS LOCAL PREPARATION PASS; DO NOT QUALIFY G6.** One genuine renderer consumer is now integrated and verified in a bounded offscreen application test. It establishes more than mocked ownership but does **not** prove interactive frame presentation, real screen scanout (GPU-02), pixel output, fully async nonblocking host rendering, physical device removal/recreation, long-run multi-consumer workloads, or a general released engine. G5 remains parked, and `G6_RENDER_LEGACY_CONTROL=1` remains a **test-only** comparison path.

**Next decision:** The most important demonstrated runtime bottleneck is the **host acceptance wait** before graphics submission; first determine whether ready accepted generations can be consumed without blocking the CPU while pending producer ticks are deferred, using only the existing fence/lease APIs. Keep rejected frames unpublished, preserve backpressure and last accepted visibility, and make no GPU solver/scheduler changes. Separately specify a bounded teardown and error policy for a truly removed D3D12 device; do not claim recovery without a real removal/recreation test. Close the stale `PH_WORK_EXTRA` API comment and report GPU/CPU latency, queue readiness and rollback in one headless matched test.

**Evidence:** `G6-P3-Real-Consumer-20261019.zip`; `DECISION.txt`, `REPRODUCE.txt`, `MANIFEST.json`, `changes.patch`, `changes/render-consumer.inc`, `changes/viewer.c`, `evidence/g6-p3/results.json`, `results.csv`, `gate-G6-P3.json`, raw offscreen timing samples, test logs and compiled D3D12/DXIL artifacts. Logged Windows results are evidence of a local developer run; this document-only update is not CI evidence.

### G6-P3 source integration with main — CONFLICTS RECONCILED / NOT A QUALIFICATION PASS (2026-10-19)

**Merge contract:** This source-integration merge joins the cumulative `g6-p3-real-consumer-20261019` development ancestry (which contains G6-P1, P2, P3 and the requalified billiards/playable source) with the separate documentation-only `main` history. The common ancestor was `4bfae94e41ccef6766a52d224a24eec907e2e378`. `main` had only three changed files since that ancestor: `README.md`, `AGENTS.md` and `docs/ENGINE_ARCHITECTURE.md`. No production C/HLSL/Zig source was independently edited on `main` since that ancestor. Therefore the exact G6-P3 code tree was preserved, with deliberate resolution of those three overlapping documentation paths.

**Conflict resolution:** Keep the current comprehensive `main` architecture record, including every G5 rejection and G6-P1/P2/P3 breakpoint; **do not replace it with the shorter stale architecture file on the G6 branch**. Keep the more complete playable/G6 development `README.md` (it already contains the link to the living architecture record from `main`) and the more detailed development `AGENTS.md`, which retains the mandatory documentation workflow and headless/short-test requirements. Correct only the stale `work-ownership.h` explanatory comment from “three” to “five” extra resources to match the already-tested `PH_WORK_EXTRA 5` contract. No solver or D3D12 behavior was modified in the conflict resolution.

**Version and status:** The merge includes historical experimental scripts and `experiments/g5-*.patch` records. Their presence **does not activate rejected solver experiments**. The restored production solver defaults remain policy 1, policy 4 opt-in; G5 is **DEFERRED / NOT QUALIFIED**. P1–P3 have bounded headless local evidence, **not** CI or formal G6 approval. The integration is a code/version-control consolidation, not a Windows GPU retest, device-recovery proof, physical displayed-FPS validation, or release candidate. Windows x64 D3D12 tests must be rerun on the actual integration head before claiming an integrated build is verified. The P3 host acceptance wait (~1.13 ms median), displayed GPU-02, real device-loss/recreation, and sustained workload coverage stay open.

**Repository hygiene after integration:** Compiled `.dxil` and `.exe`, historic release `.zip`, screenshots/videos and captured benchmark data are tracked across this historical tree. No binary was manually rewritten during this merge. Track generated/release artifacts deliberately and add a Windows CI sanity workflow in a separate scoped change, without deleting provenance evidence as part of conflict resolution.

### G6-P4 nonblocking accepted-generation rendering — LOCAL PREPARATION PASS (2026-10-19)

**Scope, version and integration:** User-uploaded `G6-P4-Nonblocking-Consumer-20261019.zip` was generated from local Windows commit `aa7d77cdfcef0efe777539aa876d2a5b05cb7ba3` on the independently pushed branch [`g6-p4-nonblocking-consumer-20261019`](https://github.com/Cryosimorgh/GPU-physics-engine/tree/g6-p4-nonblocking-consumer-20261019), based on the previously tested G6-P3 commit `621f6d626cabd2ccf187db695b658f99a80c9586`. This branch is **not merged** with `main` or the playable branch at this documentation checkpoint. Since P3, `main` integrated the earlier playable/P1–P3 source and underwent branch/history reconciliation in PRs #1/#2. **The P4 results come from the pre-integration P3 source lineage**; integrated-head source/Windows tests are still needed before promotion. The original workspace had **338 file hashes checked** and dirty working-tree status reportedly preserved. The authoritative living architecture history in `main` and playable must never be replaced by the shorter local branch copy.

**Behavior and contract:** The existing actual viewer `vrender()`, offscreen renderer and per-frame `vfinish()` are changed to allow *ordinary*, command-free frames to acquire the **latest already accepted immutable P1 snapshot** through P2 `PhWorkHandle` while a newer tick is being recorded, submitted, or awaiting validation. A graphics-queue wait on the snapshot's producer-ready fence and a registered graphics-completion fence still protect the consumer lease and resource claims; the newer producer's pending/failing generation is **not** bound for rendering. The newer tick is validated/decoded on ordered retirement, so failed ticks do not silently become accepted. User-input/command acknowledgment still takes the **matching-tick synchronous acceptance path**, preserving the command result contract. A bounded retirement/retry path handles resource error 60 (publication-slot exhaustion) before advancing an unsupported tick; failure/poison and draining semantics remain. The default nonblocking handoff is guarded by a test switch `G6_P3_BLOCKING_CONTROL=1` to compile a matched old-handshake comparison; P3's legacy renderer source-copy control remains a distinct test-only mode. This does **not** introduce a scheduler, extra GPU buffer, new CPU readback, different shader, or solver/relaxation change.

**Actual GPU correctness proof:** The archived `nonblocking-consumer-tests.inc` submits two real offscreen D3D12 renders while the **producer compute queue is held on a native test fence**, so neither newer physics fence has completed. Both renders successfully read the previously accepted generation **0**, have observed snapshot ages **one and two** ticks, and prove GPU draw work completes before the producer is released. The test also checks 64-task exhaustion, stale lease/handle rejection, blocked publication returning error **60** without advancing the tick, held immutable state across accepted later ticks, rejected generation withholding, delayed cancellation completion, and no memory allocation growth. The accompanying existing real renderer lifecycle test records **495 vertex shader invocations**, full 16-body coverage and zero reported D3D12 debug errors. No window, `Present`, image readback, actual physical device removal, or independent displayed-FPS verification was performed.

**Headless batch audit:** One final `python run_g6_p4.py` Windows batch reports **11 PASS records**: **six fresh process runs** (nonblocking, lifecycle and two AB/BA control/candidate render pairs) plus **five unchanged-binary reused tests** (publication, ownership, pool idle/collisions/energy), with original executable hashes and exact commands checked. Prior `harness-contract-failure/` logs show an obsolete test-driver assumption; it was corrected **before** the final timed batch and is not counted as a successful initial attempt. All **149** uploaded `MANIFEST.json` file SHA-256 entries match the archive, the ZIP CRC passes, and the included `verify_handoff.py` returned `PASS 149 payload hashes; no GPU work executed` on independent local verification. The archived executed driver hash, control/candidate EXE hashes and all **14** timing CSV summaries reconcile exactly against raw samples. No Windows GPU commands were rerun by this documentation review. The P4 branch comparison against P3 changes ten text/source files and **no** DXIL physics shaders.

| One offscreen 16-body workload, 32 samples per arm | Matched blocking P3 control | Nonblocking P4 |
|---|---:|---:|
| CPU acceptance wait p50 / p95 | 366.5 / 583.7 μs | **0 / 0 μs** |
| CPU total handoff p50 / p95 | 751.3 / 1,028.1 μs | **347.0 / 565.2 μs** |
| CPU record + submit p50 | 363.5 μs | 341.1 μs |
| GPU complete physics tick p50 / p95 | 602.5 / 801.75 μs | **786.5 / 873.75 μs** |
| GPU render p50 / p95 | 16.384 / 16.448 μs | **22.528 / 25.6 μs** |
| Accepted snapshot age p50 / p95 | 0 / 0 ticks | **1 / 1 tick** |
| GPU allocations / committed bytes | 39 / 2,686,976 | 39 / 2,686,976 |

**Measurement interpretation and tradeoff:** These are same-batch controls with the common `G6_P3_BLOCKING_CONTROL` instrumentation, **not** a byte-identical recreation of the preceding P3 handoff's historical **1.13-ms** acceptance-wait measurement. Report this batch's **366.5 μs → 0** improvement, not an invented paired 1.13-ms → 0 result. p50 is the **lower middle** of 32 sorted samples; p95 is the empirical nearest rank; raw samples reconcile with all 14 rows and recorded maxima. The `retirement_blocking_us` column (366.6 → 431.7 μs p50) measures an **inclusive existing frame-backpressure field**, not strictly delayed-retirement blocking. Deferred work still stalls on fence/slot reuse when necessary; the GPU physics and rendering p50 and p95 **increase** in the candidate. GPU queue overlap could contribute to wider intervals, but **hardware-level cause is unproven**; there is **no demonstrated overall throughput or FPS speedup**. The one-tick steady-state snapshot age is **7.8125 ms of simulated time** at the fixed 128-Hz step; it is **not measured display latency**, and the deliberately stalled producer observed two ticks. Performance envelopes, buffering/backpressure and visual freshness must be chosen together.

**Decision: RETAIN G6-P4 AS LOCAL CORRECTNESS/CPU-LATENCY PREPARATION PASS, NOT A FULL ENGINE PERFORMANCE PASS.** The tested nonblocking handoff safely uses previously accepted state and removes synchronous acceptance waits in normal command-free submissions while preserving the matching-tick command acknowledgment contract. However the GPU tick/render regressions, one-tick freshness tradeoff, limited 16-body offscreen test, unexplained P2 break-mode timing shift, no post-merge integrated Windows verification, actual physical device-loss and interactive GPU-02 remain open. The original G5 gate stays **DEFERRED / NOT QUALIFIED** and G6 **NOT QUALIFIED**. Keep the P4 code isolated until integrated behavior is validated; do **not** silently replace the production renderer, widen G6 release claims, or resume G5.

**Next action:** Confirm the P4 change applies cleanly to the **newly merged integrated head**, preserve current `docs/ENGINE_ARCHITECTURE.md` and both branch ancestries, run one focused Windows real offscreen consumer plus physics/ownership regression check there, and report measured CPU/GPU/age tradeoffs. After that, address **bounded device-loss detection, teardown, invalid lease/queue cleanup and explicit reinitialization limits** as a separate G6 preparation checkpoint. Injected errors may validate the software failure paths; only real device removal and re-creation tests can qualify physical recovery. No viewer screenshots, mass benchmarking, speculative scheduler or FP64 solver experiments.

**Evidence:** `G6-P4-Nonblocking-Consumer-20261019.zip`, `DECISION.txt`, `REPRODUCE.txt`, `MANIFEST.json`, `changes.patch`, `changes/{viewer.c,render-consumer.inc,nonblocking-consumer-tests.inc,...}`, `evidence/g6-p4/{results.json,results.csv,nonblocking.json,gate-G6-P4.json}`, archived logs, DXIL and candidate/control executable hashes.

### G6-P5 integrated nonblocking renderer — SELECTABLE, BLOCKING DEFAULT (2026-10-19)

**LOCAL INTEGRATION PASS; formal G6 NOT QUALIFIED; G5 DEFERRED / NOT QUALIFIED.** This breakpoint starts at merged main `f32798ba09f8`, not the older P3 head. A real merge retains P4 `aa7d77cdfcef` and main as parents. Main's complete architecture document and repository inventory are preserved; the conflicted older P4 document was not substituted. Earlier P4 audit statements about unmerged source describe their historical review point; this P5 decision supersedes that integration status.

**Integration scope and default:** Main differed from P3 only in accumulated architecture/inventory records and the already-correct five-resource comment. Necessary P4 renderer ownership, deferred-retirement helpers and headless tests were integrated. `ViewerConfig.nonblocking` explicitly selects matching-tick mode (`0`, default) or last-accepted-generation mode (`1`). The reference CLI, benchmark and playable entry points accept `--nonblocking 0|1`; zero-initialized application config preserves main's default behavior. Interactive scene requests copy the same config. Invalid selection is rejected. The previous direct consumer-test API remains available for P3/P4 tests; current headless measurements select their mode explicitly.

Both modes bind immutable accepted snapshot buffers and P2 dependencies, register consuming queue/fence ownership before submission, queue-wait for the leased generation's readiness and release only after completion. Nonblocking ordinary frames may draw the previous accepted generation while a newer tick is pending; promotion remains at ordered validation/retirement. Prepared/submitted cancellation, explicit capacity pressure and bounded frame-slot retirement are unchanged. Command-bearing frames still wait for the matching tick and status word. Physics impact event identity is the validated simulation generation. No physics source, solver math, shader, KKT tolerance, fixed tick or rollback rule changed; all 85 DXIL outputs match the retained P4 working tree. No scheduler or extra renderer GPU allocation was added.

**Bounded Windows proof:** `python run_g6_p5.py` builds/reuses verified source/tool/options/output caches, then serializes one bounded CLI batch. Final evidence has **20 PASS records: 12 fresh process runs plus eight checks reused only with exact command/executable and, for syntax checks, input hashes**. Three application CLI files pass syntax checks; the actual C/D3D12 renderer and C++ host are compiled into both headless executables. This does not claim the graphical applications were launched. Default and opt-in consumers, native gated-producer draws, delayed consumers, private-buffer poisoning, rejection/rollback, matching-tick command acknowledgement, generation reuse/stale handles, 64-lease exhaustion, prepared cancellation/submitted failure and cleanup pass. Publication/ownership and pool idle/collision/energy regressions pass. No unfinished or rejected generation is bound by the real draw tests.

An initial fixture defect left a one-tick command in the upload buffer. Both modes correctly rejected tick 1 with error 128. The fixture now clears the command on inactive ticks exactly as existing pool tests do. The failed batch, logs, driver and source are retained under `fixture-command-failure`; validation was not relaxed. The corrected comparison uses newly matched final-source binaries for all eight timing trials. Unaffected physics and syntax checks were reused; all timed comparisons were rerun consistently after the fixture fix.

The timing batch uses existing separate compute/graphics queues, two 16-body fixtures, four warmup and 16 measured frames per process, and AB/BA repeats: **32 timed frames per mode per workload, 128 timed / 160 total verified frames**. Complete-frame wall time includes command upload when present, CPU record/submission, both GPU completions and readback/validation of the actual draw. Final full body-buffer FNV-64 signatures match across modes/repeats, outside timing; existing independent physics regressions remain the physical reference. All command frames have age zero; ordinary opt-in frames have age one. Gated-producer tests additionally demonstrate age two without premature publication.

| Workload / metric | Blocking p50 / p95 | Nonblocking p50 / p95 |
|---|---:|---:|
| Idle: pre-submit acceptance wait, us | 560.7 / 1162 | 0 / 0 |
| Idle: CPU record + submit, us | 376.8 / 721 | 374.2 / 673 |
| Idle: CPU queue submission, us | 124.2 / 458.8 | 124 / 410.8 |
| Idle: complete CPU handoff, us | 947.5 / 1778.9 | 383.2 / 683.6 |
| Idle: GPU tick interval, us | 790.5 / 1393.5 | 796.75 / 1204 |
| Idle: GPU render interval, us | 16.384 / 18.752 | 23.552 / 26.624 |
| Idle: complete frame wall time, us | 1023.9 / 2031.7 | 1079.6 / 1510.5 |
| Idle: snapshot age, ticks | 0 / 0 | 1 / 1 |
| Pool motion / commands: pre-submit acceptance wait, us | 402.3 / 588.8 | 0 / 410.4 |
| Pool motion / commands: CPU record + submit, us | 292.7 / 322.3 | 272.9 / 307.8 |
| Pool motion / commands: CPU queue submission, us | 48 / 59.5 | 39.2 / 53.9 |
| Pool motion / commands: complete CPU handoff, us | 706.4 / 880.8 | 281.1 / 759.7 |
| Pool motion / commands: GPU tick interval, us | 365 / 370 | 366.5 / 370.75 |
| Pool motion / commands: GPU render interval, us | 18.432 / 20.48 | 22.528 / 25.6 |
| Pool motion / commands: complete frame wall time, us | 836.8 / 1503.8 | 664.9 / 1173.1 |
| Pool motion / commands: snapshot age, ticks | 0 / 0 | 1 / 1 |

| Workload | Blocking complete frames/s | Nonblocking complete frames/s | Committed bytes / allocations, either mode |
|---|---:|---:|---:|
| Idle | 875.765 | 941.498 | 2,686,976 / 39 |
| Pool motion / commands | 1061.652 | 1324.059 | 2,752,512 / 40 |


Throughput is total completed measured frames divided by the sum of complete-frame wall intervals, not reciprocal median latency, Present rate or displayed FPS. Common offscreen coverage-query instrumentation and validation are included. Initialization, warmup, final signature readback and teardown are excluded. These serial complete-to-complete frames do not establish sustained application throughput at a larger frame backlog or on a physical display. `retirement_blocking_us` remains the historical inclusive backpressure field; use explicit acceptance and complete-frame wall timings above rather than interpreting that field as pure retirement time.

The current GPU **tick** median regression is small (about 0.8% idle, 0.4% pool), unlike P4's earlier approximately 30% observation. GPU **render** medians still increase (16.384→23.552 us idle, 18.432→22.528 us pool). No hardware-counter attribution is proven. Pooled measured frame throughput improves about 7.5% idle and 24.7% pool, but idle median frame latency worsens (1023.9→1079.6 us), ordinary snapshots are one fixed tick older, and these are short local measurements. Pool motion/command timings contain **zero contacts** in this short window; collision/energy correctness comes from the separate targeted regressions, not a collision-throughput claim. The idle workload records 16 contacts across each arm's 32 measured ticks. Command frames are four of the 32 timed pool frames per mode and retain acceptance waits (nonblocking p95 410.4 us).

**Decision:** Keep nonblocking available as an explicit latency/freshness tradeoff; **blocking remains the unconditional default**. The limited benefit is useful for opt-in experiments, but does not justify changing general application freshness or claiming a universal GPU/throughput improvement. No added GPU committed bytes or allocations occur between modes. A one-tick simulation age at 128 Hz is 7.8125 ms of simulation time, not measured photon/display latency. Same-queue and sustained interactive throughput were not measured here. P1/P2 break timestamp attribution remains unresolved and is not used in this decision.

Evidence: `evidence/g6-p5/{integration.json,baseline-test.json,results.json,results.csv,throughput.csv,reconciliation.json,gate-G6-P5.json}`, per-process raw JSON/logs, source/binary hashes, and the focused ZIP. `python verify_g6_p5.py` independently reconciles all 32 metric rows, four throughput groups, full-state signatures, command ages and unchanged per-workload memory. The original workspace retains all 340 recorded tracked-file hashes and dirty status. Physical device loss/recovery, GPU-02/display and formal G6 remain UNVERIFIED / NOT QUALIFIED. The next separate task is device-loss detection, safe ownership teardown and recovery-boundary validation; no removal/recreation test was performed here.

**Independent handoff audit (2026-10-19):** The uploaded `G6-P5-Integrated-Rendering-20261019.zip` passed full ZIP CRC and **193/193** manifest-listed SHA-256 file checks. All **16** uploaded `changes/` file Git blob IDs match the actual `main` commit tree at `5d311523b0663965e0d36699e35fb836345376eb`; the two merge parents also match the handoff. Separately recomputed medians (lower-middle of 32) and p95 nearest-rank for all **32** CSV metric rows, and all **four** throughput rates from the original eight × 16-frame trial series: **zero mismatches**. There are **12 fresh and 8 exact-input-reused** PASS process records (including one expected invalid-option exit), not 20 independently rerun tests. The original stale-command failure was retained and the corrected fixture re-executed with matched control/candidate binaries. This reviewer did **not** run Windows D3D12 tests or qualify displayed frames, large collision networks, device removal or sustained rates. No additional solver/source change was made by this audit. 

### G6-P6 failed contexts, teardown and explicit recreation — LOCAL PASS (2026-10-19)

**G5 remains DEFERRED / NOT QUALIFIED. Formal G6 remains NOT QUALIFIED.** Work starts at latest integrated main `930eb34e4307` and preserves the P4/P5 merge ancestry and the full audited architecture record. This is a failure-lifetime boundary, not a new solver, scheduler or automatic game-state recovery system. All 85 DXIL outputs and the physics/solver HLSL sources match the retained P5 workspace exactly.

#### Audit and explicit failure state

Previously `gp_submit()` / `s_submit()` could terminate the process on a failed post-Execute Signal, while other API/wait failures returned without permanently failing the context. A removal sentinel was not a completion proof. Renderer and physics ownership also needed a checked close API and a CPU owner link to prevent freeing physics underneath a live renderer.

`GP.failed`, first error and removed reason are sticky. `gp_ok()` records failed native calls; `gp_removed()` queries the actual device reason. Queue submission/Signal and renderer queue Wait/Signal/Present use this failure path. Fence waits check errors, use finite waits and recheck the actual fence after waking. `UINT64_MAX` is never successful completion. Runtime ACTIVE, FAILED, REMOVED and QUIESCING are explicit (`s_device_state/info`). New allocations, command recording/submission, maps and resource claims are rejected on a failed/stopping context; snapshot/task operations fail closed through `s_completed()`. Logical physics rejection remains separate from device failure and retains its existing rollback/last-accepted-state behavior.

After Execute but before a successful Signal, `GP.unfenced` blocks normal reclamation. A failed wait is not proof of GPU completion or removal. Cleanup may issue a genuine terminal Signal on the same queue after earlier work, then observe its fence. That is cleanup synchronization, not restarting physics. The failed flag is never cleared by later successful cleanup calls. Native graphics teardown also places a terminal fence after prior queue/Present work. The actual Present/swap-chain removal path remains untested because this task is headless.

#### Ownership, teardown and recreation contract

`viewer_try_close(Viewer **, timeout_ms)`, `ph_teardown(Physics **)` and `s_try_close(StorageDevice **, timeout_ms)` clear the owner pointer only after successful destruction; calling them again with NULL succeeds. Renderer CPU ownership prevents closing physics first; runtime state owners and outstanding claims prevent closing the device first. Normal viewer close leaves its healthy parent context usable. Legacy void close wrappers make one checked attempt and log quarantine on failure; they do not implement retry/recovery and must not be called again with a freed raw pointer. Applications that need recovery must retain owner pointers and use the checked APIs. Existing application fail-fast behavior is not an automatic GUI recovery loop.

Healthy or merely failed-but-not-removed GPU work must drain. `ph_failure_cleanup()` refuses incomplete consumer fences, keeps leases/resources pinned and invalidates failed publications. Only after proof may it drop task/queue/fence references and claims. `s_drain()` cancels unsubmitted recording bookkeeping, bounds waits and handles the unfenced compute interval; `s_quiesce()` stops further use before final context destruction. A final audit also fixed the headless physics-owner path: failed physics teardown drains/discards recording state before retiring any buffer, including actual removal with an open, unsubmitted list and no renderer owner.

Confirmed native device removal is terminal cancellation, **not accepted task completion**. It permits releasing canceled GPU work without waiting for ordinary completion values that the removed device cannot produce. The proof is the actual native removed reason, not an injected `DXGI_ERROR_DEVICE_REMOVED` HRESULT or a timed-out wait. Microsoft's [RemoveDevice contract](https://learn.microsoft.com/en-us/windows/win32/api/d3d12/nf-d3d12-id3d12device5-removedevice) describes the unusable device and removal fence sentinel. CPU test workers must finish before their fence references are freed. Without completion/removal proof, the checked API returns failure with ownership intact; it never frees possibly referenced GPU objects to force progress.

Host buffer handles retain the same 64-bit shape, but allocation generations now use the checked process-wide monotonic identity source rather than restarting at generation 1 in each context. Values above UINT32_MAX reject allocation instead of wrapping. Entity IDs, component layout and shader constants are unchanged. Task/lease device/context identities and buffer generations prevent old handles from naming a fresh context's resources.

Recreation is an explicit caller operation after old renderer/physics/device owners and claims have been released. It calls D3D12CreateDevice through the existing `s_open` path, creates fresh storage, initializes a **new scene**, and uses new identities. No failed context becomes ACTIVE again. This implementation does not transfer an unreadable removed-device snapshot, restore a checkpoint, promise trajectory continuation or silently recover an application. Controlled native API removal/recreation is tested below; physical TDR, power loss/hot unplug and driver-failure recovery are not.

#### Focused Windows evidence

`python run_g6_p6.py` builds/reuses verified artifacts and runs one serialized final batch with 90-second process bounds. **16/16 final process runs pass**, all freshly executed on final source. Eight device scenarios each tear down the old context, reject stale raw/task/lease handles on the replacement context and execute real offscreen GPU rendering in both modes. The other eight checks cover blocking/opt-in consumer lifecycle, gated pending-generation isolation, publication/ownership, and pool idle/collision/energy regressions. Healthy-device scenarios also check zero D3D12 validation errors. No window, Present, screenshot/video or broad performance campaign is used.

| Case | Mechanism | Terminal context | Fresh GPU modes |
|---|---|---|---:|
| 0 | normal pending-consumer shutdown | ACTIVE | 2 |
| 1 | injected Close failure before Execute | FAILED | 2 |
| 2 | injected compute Signal failure after Execute | FAILED | 2 |
| 3 | real timeout behind held consumer gate | FAILED | 2 |
| 4 | injected compute wait failure | FAILED | 2 |
| 5 | API-triggered D3D12 RemoveDevice | REMOVED | 2 |
| 6 | injected graphics Signal failure after Execute | FAILED | 2 |
| 7 | API removal during unsubmitted recording without renderer owner | REMOVED | 2 |


Cases 1/2/4/6 inject failure HRESULTs at explicit Close, post-Execute compute/graphics Signal or wait points. Case 3 is a real bounded wait timeout caused by a deliberately held consumer gate on a healthy device. Cases 5/7 execute **ID3D12Device5::RemoveDevice** and observe the actual removed reason; case 5 observes both producer and consumer fences at UINT64_MAX. They then destroy the old objects, create a fresh device/context and execute both GPU render modes. These are controlled real D3D12 runtime removals, **not physical hardware faults**. All failed contexts block new publications/submissions, all cases end with zero owners/claims, and the Zig owner checks zero runtime buffer handles before final device close.

The held-consumer/failed-Signal tests first reject cleanup without reducing live buffer or claim counts, then release their legitimate test gate and observe a genuine queue completion before successful cleanup. Repeated checked teardown succeeds; fresh IDs differ and old buffer/task/lease handles fail. Recorded viewer close durations for cases with a live viewer are about 8.3–28.7 ms; the 5-ms failed-cleanup waits observe about 8.3–16.6 ms wall time. These include scheduling/native-call overhead and are not hard real-time guarantees. `cleanup_us` covers `viewer_try_close` only, excluding later physics/device destruction and recreation; case 7 had already closed its viewer, so its tiny raw value is not a total recovery-time result. No new GPU buffers/copies are needed for the lifecycle mechanism; normal-tick performance was not requalified.

Evidence: `evidence/g6-p6/{results.json,results.csv,source-audit.json,physics-host-scope.patch,reconciliation.json,gate-G6-P6.json,original.json}`, exact commands and full per-process logs. `python verify_g6_p6.py` reconciles classifications, terminal states, fresh IDs, repeated close, zero claims and all 16 new-context render-mode proofs. One reserved-identifier build failure ran no GPU tests; the preceding 15/15 pass was preserved before the final recording-boundary fix. Root results are authoritative. All 343 original tracked-file hashes and original dirty status remain unchanged.

**Verdict:** The tested failure/teardown/new-scene boundaries pass locally. Blocking remains the application default; nonblocking remains explicit, with matching-tick command acknowledgement and unchanged physics rollback. Physical hardware-fault recovery, checkpoint continuation, actual GUI/Present recreation and strict driver-call deadlines remain UNVERIFIED. G5 is deferred; G6 remains unqualified. Next: independently review this evidence and separately qualify any required physical/driver-fault and application recovery paths; do not resume G5.

**Independent G6-P6 handoff audit (2026-10-19):** The uploaded `G6-P6-Device-Loss-Safe-Teardown-20261019.zip` passed CRC, all **210/210** manifest-listed SHA-256 file checks and execution of the supplied offline `verify_handoff.py` (**PASS 210**; no GPU commands executed). The published `main` revision is `96a548ebb2eb2658c368e1454b4369d30524415d`, directly descended from the audited P5 main `930eb34e4307798b0f3d5acc33ce3dca2fed3db1`. All **18** manifest-declared changed Git blob SHA-1 values match the actual main tree; **85 shader DXIL** outputs remain the prior source/output set without modified shader files. The underlying `results.json` contains **16 distinct final process entries**, each with `returncode=0` and `PASS`; eight device cases classify as **four injected API failures, one real held-queue timeout, one normal pending-consumer shutdown, and two actual API `ID3D12Device5::RemoveDevice` cases**. Every device case reports newly created context identity, both fresh GPU render modes, stale-handle rejection and repeated teardown success; the two native removals are verified as **controlled API-triggered runtime removal**, not a physically induced GPU crash/TDR. Prior reserved-word build failure and passing 15-case precursor are retained separately, not counted as fresh final successes. The original-workspace preservation count (343) is reported by the Windows handoff; it cannot be independently reconfirmed from the ZIP. **Recorded Windows D3D12 tests were not rerun by this reviewer**. `cleanup_us` is only viewer close time and is not total failure-recovery latency. This independent audit makes **no** claim of physical driver/hardware fault recovery, GUI/swapchain restoration, checkpoint continuation, sustained performance, or G6 foundation qualification.

## 9. Global time, sleeping, and simulation state

**Code:** `physics.c`, `physics.hlsl`, `viewer.c`.

The simulation uses one global fixed timestep. The controlled physics fixtures use **1/128 second**. The rendering rate can differ from the physics rate. Sleeping means that some work can be skipped; it must **not** give an entity its own simulation clock.

The intended state contract is:

1. Read the completed state `S(t)`.
2. Apply user commands at the tick boundary.
3. Calculate a provisional next state in scratch storage.
4. Detect and solve contacts using ordered GPU passes.
5. Run global validation and guard checks.
6. Publish only the accepted `S(t+1)` generation.
7. Allow rendering to consume a completed, versioned generation.

**Current qualification:** The code has separate passes, a provisional trial buffer, validation checks, and generation diagnostics. However, G4 still publishes into the original source buffer per body after validation. A full immutable-source and atomic-generation-swap implementation is **not yet proven**. This is a required production gate, not an optional style change.

The project tests rejected ticks and rollback behavior. A rejected attempted state must not be called a completed simulation result.

## 10. Fast paths and GPU-driven work control — later local experiments

A sequence of local experiments reduced the reported headless 16-ball idle tick from roughly **669 µs to 249–251 µs**. The improvements include:

- Skip costly square roots for pairs that are clearly too far apart, while keeping precise checks close to contact.
- Use GPU-side predication to bypass graph and solver work when no work is required.
- Stop redundant discovery rounds when the previous GPU result proves no more rounds are needed.
- Reduce the number of CPU command-list submissions for the idle path.

These figures are **headless, workload-specific handoff measurements**. They are not the same measurement as the graphics viewer's complete frame time. They are also not evidence of faster active large-island solving.

**Innovation / value:** GPU-side decisions reduce both wasted GPU passes and CPU synchronization. The engine can leave the state on the GPU and still avoid unnecessary work. Predication and early termination must preserve wake-up, the first new contact, error flags, and validation.

## 11. Rendering, presentation, and interactive use — G4

**Code:** `viewer.c`, `render.hlsl`, `hud.hlsl`; on the playable branch also `play_ui.cpp`, `playground_view.inc`, `pool.hlsl`.

The viewer draws GPU-resident positions without reading back all entity coordinates. It supports one to three frames in flight. The render path can consume a protected snapshot. Swap-chain, queue, and fence ownership control when graphics resources can be reused.

The G4 demonstration draws two-dimensional disks as shaded sphere impostors. On large overview scenes, it may render **at most 50,000 samples** while the GPU still simulates all entities. Rendered instance count and simulated entity count are separate metrics.

The later playable branch adds a 16-ball pool scene, cue input, physical rail and cloth parameters, and live telemetry. It is a **planar billiards approximation**; pockets, scoring, elevated cue strikes, and full 3D ball dynamics are not qualified features.

**Historical G4 mixed-billiards measurements:** 10K bodies about **1.85 ms**, 100K about **5.47 ms**, and 1M about **43.71 ms** per physics tick (reported p50 in the G4 handoff). These figures cannot be compared directly to the synthetic G1/G2 kernels or to later playable-pool frames.

The distinction between metrics matters:

| Metric | What it measures |
|---|---|
| Physics ticks per second | Accepted global simulation steps per second. |
| GPU physics time | GPU timestamps around defined physics work. |
| CPU record/submit time | Host work to build and submit GPU commands. |
| Render FPS / Present calls | Application rendering or presentation activity. |
| Physical displayed FPS and scanout delay | Display-system evidence, which can be unavailable in RDP. |

**G4 status:** Conditionally accepted for scoped simulation/render execution. Formal physical-display correlation (**GPU-02**) remains **unverified** unless a local trace closes it.

### G6-P7 real viewer/display attempt — APPLICATION PASS / GPU-02 UNVERIFIED (2026-10-19)

**Base and scope:** `g6-p7-display-qualification-20261019` starts at current main `d498c5862d855d20e8e2be232706ab3fed09befd`. The prior P6 working tree, dirty status and all 348 tracked-file hashes are unchanged. All 85 retained DXIL outputs and the solver source match that workspace. G5 remains **DEFERRED / NOT QUALIFIED**; formal G6 remains **NOT QUALIFIED**. No physics, policy, timestep, tolerance or production-default change was made.

**Audit and instrumentation:** The actual playground uses a windowed BGRA8 triple-buffer flip-discard swap chain, maximum frame latency equal to the bounded slot depth, and an existing direct queue shared by physics and rendering in this host configuration. Each render leases only an accepted immutable snapshot, registers the graphics fence before Execute, and expresses the ready-fence wait on that queue. Commands retain matching-tick acceptance. The interactive loop uses fixed 1/128 ticks, CPU tick pacing, slot/back-buffer fence waits and Present/VSync backpressure; it creates the DXGI frame-latency handle but does not explicitly wait on it in the interactive loop. The observed acceptance wait includes queue/presentation pacing and is not a solver duration.

`SUBMITTED`, `PRESENT_RETURN` and retired `FRAME` records now identify each image by process/session + epoch/frame, swap-chain address, back-buffer index, accepted generation, submit/present QPC, graphics fence and GetLastPresentCount. **GetLastPresentCount is an API correlation identifier, not a displayed event.** A bounded exact-generation clock lookup records the rendered snapshot's simulation start separately from the newer attempted tick; zero explicitly means initial/unknown. Snapshot age is measured when the lease is acquired, not at later retirement. Logging uses the existing bounded asynchronous writer; there are no extra GPU buffers, readbacks or per-frame flushes. The existing GPU generation/epoch/coverage checks remain mandatory. Five focused CPU evidence tests pass; raw frame records pass independent offline reconciliation against the build manifest.

**One actual Windows display session:** The read-only QueryDisplayConfig/WTS probe establishes local process/active console session 1, non-remote session, one active EDID-valid VG27AQ3A HDMI target, 2560×1440 desktop at 120/1 Hz. An inactive installed Meta virtual display is not the active path. PresentMon 2.6.0 (official release SHA-256 in preflight evidence) exits **6: failed to start trace session, access denied**. Administrators is deny-only in the medium-integrity token; Performance Log Users is absent. No elevation, group change, equivalent failed retry, ETL or OS present/display CSV occurred. Consequently displayed images/FPS, per-image simulation-to-display latency, dropped images, repeated refreshes and actual scanout remain **UNVERIFIED / null, zero valid display-latency samples**. Present count, GPU timestamps, DWM timing and refresh rate are not used to fill that gap. Future ETW-derived display estimates must also remain distinct from optical photon latency.

The single 21.75-second serialized application batch ran four normal ABBA repetitions (blocking, nonblocking, nonblocking, blocking), then controlled native ID3D12Device5::RemoveDevice once per mode. The same verified EXE/shaders, 16-ball profile 13, 1.5 m/s bounded cue command, depth 2, VSync 1 and 1280×800 client configuration were used. Automated Win32 messages exercise the existing command upload, acknowledgment and pause/resume path; these are not physical input-latency measurements. Each normal run completed **298 frames / 286 ticks**, with **137 contact-bearing ticks**, **18 maximum contacts**, **15-body maximum island**, **409 contact observations** (not distinct contacts), one matching-generation impulse acknowledgment, pause/resume and clean process exit. Six application cases pass; telemetry drops and reported validation flags are zero. Native debug-layer/GPU-based validation was not enabled for these timing runs.

| Pooled normal runs; nearest-rank quantiles | Blocking | Opt-in nonblocking |
|---|---:|---:|
| Completed frames / simulated ticks | 596 / 572 | 596 / 572 |
| GPU physics p50 / p95 / p99, ms | 0.2905 / 1.39675 / 1.61625 | 0.2910 / 0.88275 / 1.3565 |
| GPU render p50 / p95 / p99, ms | 0.0256 / 0.033792 / 0.034816 | 0.0256 / 0.026624 / 0.031744 |
| CPU acceptance wait p50 / p95, ms | 7.3644 / 7.8947 | 0 / 0 |
| CPU submission p50 / p95, ms | 0.0724 / 0.1052 | 0.0790 / 0.1052 |
| CPU loop-body frame p50 / p95 / p99, ms | 8.0263 / 8.5396 / 8.7961 | 0.6607 / 16.1984 / 16.3081 |
| Accepted snapshot age p50 / p95, ticks | 0 / 0 | 1 / 2 |
| Automated message-to-ack, two samples, ms | 15.5585–15.8574 | 14.3495–14.3741 |
| Peak accounted commitment / runtime buffer allocations | 17,694,720 bytes / 39 | 17,694,720 bytes / 39 |
| Displayed FPS / valid display-latency samples | UNVERIFIED / 0 | UNVERIFIED / 0 |

CPU loop-body duration excludes time outside that loop iteration and is not displayed-frame latency or whole-frame throughput. GPU physics/render intervals are separate stage measurements; they do not prove an externally observed complete GPU/display frame latency. The small ABBA sample is local evidence, not a general performance win. Nonblocking improves median CPU blocking but has a roughly 16.2 ms CPU frame p95 and older accepted state. Keep blocking as the default. The allocation count covers runtime ledger buffers, not a census of native D3D12 internal allocations; GUI/back-buffer commitment is charged separately. Per-frame DXGI Budget/CurrentUsage and tracked commitment are retained in raw records; OS usage includes other allocations/processes and is not per-application residency proof.

**Controlled removal boundary:** The application detects actual API removal, stops submitting/Presenting, reports EXPECTED_DEVICE_REMOVAL_STOP, and completes checked viewer → physics → bundle → device teardown. Both modes exit 0 through this opt-in test path. There are 296/297 retired frames from 298 submitted images respectively; removal invalidates the remaining in-flight work, which is not counted as completed or displayed. There is no new submit/Present after the removal request. No recreation, checkpoint continuation, GUI restoration, physical fault/TDR or hardware recovery was tested in P7. Outside the explicit test path, existing production fail-closed behavior is preserved.

**Decision:** Retain scoped telemetry/test controls and the application verification. **Do not close GPU-02 or qualify G6.** Minimum next local-console step: run PresentMon with an elevated token, or have an administrator grant Performance Log Users and sign out/in, then capture the same bounded ABBA scenarios with QPC/display tracking and retain the external raw trace. Correlate every image using process/swap-chain/Present identifiers plus QPC (validate identifier domains; do not assume equality), reject ambiguous/missing events, account for VSync/drops/repeats, and repeat before a display claim. Physical photon latency still requires an optical instrument. This permission boundary was not bypassed.

**Evidence and reproduction:** `G6-P7-Display-Qualification-20261019.zip`, `evidence/g6-p7/{session.json,comparison.csv,pooled.json,pooled.csv,gate-G6-P7.json,verification.json}`, all six `process.log`/raw `samples.json`/`samples.csv`, pre/post display metadata and PresentMon permission/tool logs. Commands from the isolated root: `python display_probe.py`; `python build_billiards.py`; `python -m unittest test_g6_p7 -q`; `python run_g6_p7.py` (one session; refuses overwrite); `python verify_g6_p7.py` (offline only). Full architecture history and P1–P6 evidence are preserved.

**Independent archive and GitHub review (2026-10-19):** Audited the user-uploaded `G6-P7-Display-Qualification-20261019.zip` (648,932 bytes, 79 ZIP entries). CRC is intact, **78/78** manifest-listed SHA-256 entries match, all archive entries are accounted for, and the bundled offline `verify_handoff.py` returns **PASS** with six real-window runs reconciled. All **13** changed source/document files have exact Git blob hashes matching the committed P7 branch revision `0df58576a335364876b64f233f8fac30fea82571` (parent `d498c5862d855d20e8e2be232706ab3fed09befd`); no shader/DXIL source was changed. Independently checked raw telemetry in all **six** cases: four normal runs have 298 submitted, 298 Present-returned, 298 fence-completed frames each (286 simulation ticks, 137 contact-bearing ticks, max 18 contacts and max island 15). Two controlled RemoveDevice cases have 298 submitted and returned Presents but only **296/297 retired GPU frames**, respectively; in-flight frames are not counted as displayed or completed. Each case contains one matched cue acknowledgment, PAUSE and RESUME and no reported dropped telemetry, errors or generation/QPC-order mismatch. Recomputed all **16** normal pooled raw quantile groups (eight fields for each mode) with nearest-rank quantiles: exactly matched `pooled.json`. Five recorded CPU unit tests passed. PresentMon's archived `permission.log` says **failed to start trace session: access denied**, and the ZIP contains **no OS ETL/display trace**. Thus **GPU-02, displayed FPS, repeated/dropped presented images and display latency remain UNVERIFIED** despite an active EDID-valid 120-Hz local HDMI path. The original Windows working-tree preservation is reported by the developer, not independently tested here; these are recorded Windows results, **not independently rerun Windows D3D12 execution**. P7 remains an isolated development branch: its instrumentation was **not merged** into `main` or the playable source by this documentation update. No unauthorized elevation or new tracing was attempted.

## 12. Billiards material physics — playable branch

**Code:** `pool.hlsl`, `pool-schema.json`, `pool_tests.zig`, `test_billiards_physics.py` on the playable branch.

A scientific stress test must keep contacts active to measure throughput. A realistic pool game must behave differently:

- One cue ball and 15 numbered object balls begin at rest.
- A cue strike adds a bounded impulse at a global tick boundary.
- New impacts use restitution; resting contacts must not bounce repeatedly.
- Rails apply normal restitution and tangential response.
- Cloth friction transfers motion from sliding to rolling and then slows the ball.
- Sleeping and exact stopping prevent idle drift.

The playable branch reports independent tests for collision impulses, energy, rolling, sleep/wake, and a long stationary-rack run. Material settings are **chosen parameters**, not certified measurements of a commercial table. This scene is not a replacement for the frozen scientific G4 fixtures.

**Engineering lesson:** Separate a physical product demonstration from a synthetic stress workload. Otherwise the test's artificial forces and initial velocities appear as game-physics defects.

## 13. Verification and low-cost test workflow

**Code:** `physics_verify.c`, `physics_tests.c`, `tests.zig`; on the playable branch `dev_test.py`, `test_dev_workflow.py`, and the billiards test scripts.

Validation has several levels:

1. **Unit contracts:** Checked arithmetic, entity identity, mappings, generation reuse, and transaction rollback.
2. **Small analytical physics tests:** Head-on and oblique impacts, friction, rails, energy and momentum checks.
3. **GPU correctness runs:** Contact count, island size, residuals, guard regions, rejected-state behavior, and resource ownership.
4. **Comparative performance:** Identical fixtures and hardware; separate CPU, GPU, renderer, and presentation costs.
5. **Full gate qualification:** Broader workload coverage and a recorded report. It is not part of every code edit.

For routine physics work, use the **headless CLI**. The playable branch's `python dev_test.py` supports quick, affected-file, and full levels. Its build cache hashes the source dependency graph, compiler, options, and output artifacts; it must not trust timestamps alone.

**G5 sweep method:** Run all specified topologies in one sequential CLI batch; write JSON/CSV evidence; show one compact summary. A two-sample quick sweep is exploratory. Do not treat its p95 as a stable tail-latency estimate.

Screenshots and video belong to an explicit **graphics/UX** task or a release milestone. They are not necessary to prove headless solver correctness.

## 14. Main technical contributions and their limits

These are **engineering contributions**, not claims that a method is new to computer science.

| Area | Contribution | Current limit |
|---|---|---|
| GPU-first state | Keep hot simulation data resident on the GPU. | Some setup, command, and diagnostics still use the CPU. |
| Entity lifetime | Generation-safe identity with GPU dense storage and verified growth. | Growth can stall; capacity and active count differ. |
| Measured layout selection | Compare AoS, SoA, and AoSoA before choosing SoA. | Selection depends on the measured passes. |
| Spatial search | Compare hash and radix under real candidate workloads. | Search speed does not imply fast constraint solving. |
| Island-level solve | Detect and process independent contact graphs; color conflicting contacts. | Large connected islands remain costly. |
| Numerical verification | Combine KKT residuals, energy checks, guards, and rollback. | Strict source-buffer isolation remains open. |
| GPU fast paths | Predication and early exit without per-tick CPU readback. | Local 16-ball measurements are not large-scene proof. |
| Rendering link | Draw completed GPU state with measured queue ownership. | Displayed FPS/scanout qualification remains open. |
| Reproducible test loop | Deterministic fixtures, hash-checked builds, headless batch sweeps. | Local handoffs must be committed or archived to persist. |

A high entity count is a storage and dispatch result unless the test also reports actual contacts, island structure, convergence, and accepted ticks.

### G6-P8 sustained headless physics — LIMITED ENVELOPE / POOL FAILURE (2026-10-19)

**Base and preservation:** `g6-p8-sustained-qualification-20261019` starts at current main `b4754a1606c2e7d3ca42f92c0d5b462b82544593`. The original P7 workspace, all 354 tracked-file hashes and dirty status are preserved. All 85 retained DXIL files, `physics.c`, `physics.hlsl`, `pool.hlsl`, `projected_solver.hlsl`, solver policies, fixed global dt, tolerances and production defaults are unchanged. P7 display status remains **GPU-02 UNVERIFIED**; no viewer or tracing tool ran. G5 remains **DEFERRED / NOT QUALIFIED** and formal G6 remains **NOT QUALIFIED**.

**Existing infrastructure and bounded session:** The existing `physics.exe` gets an opt-in `--seconds 1..30` measurement branch, implemented by `sustained_physics.zig` using the existing storage, `ph_scene`, `ph_tick`, `ph_verify`, command upload, failure injection and cleanup APIs. The ordinary steps-based path is preserved. JSONL streams each tick directly to disk with a 100,000-tick safety bound; no million-entry descriptor arrays are allocated. `run_g6_p8.py` uses verified `dev_test.py` build caching, runs GPU cases sequentially and stops a failing process immediately. It launches no renderer. The baseline CLI rejected `--seconds` before GPU startup. One consolidated batch ran the existing collision and energy CLI regressions, then three scenarios. Seven final CPU evidence tests pass. The initially recorded batch returned zero despite its failed child; this orchestration defect is corrected to return nonzero for any failed case, without repeating GPU work. The original result is retained in `results.recorded-batch.json`.

Thirty seconds means **wall-clock test-session duration**, excluding initial creation, and does not mean 30 simulated seconds. Every tick still advances dt=1/128; both durations are recorded. Throughput includes full CPU reference validation, readbacks and streaming evidence, so it is a conservative tested cadence, **not maximum production throughput**. Physics GPU timestamps and CPU record/submit intervals exclude that outer CPU oracle. No sustained 128-Hz qualification is claimed.

**Reused physically valid fixtures:** Small: profile 13, 16 stationary rack balls, real default billiards material, radius 0.028575 m and 2.54×1.27 m table. The existing bounded cue command applies ±1.5 m/s only when all linear, yaw and rolling motion is exactly at rest. Nine shots were submitted before failure; this is ordinary rest-gated input, not repeated state resets or overlapping fixtures. Medium and large: existing profile 10 with **external drive disabled** (`flags=4`), 1,024 / 8,192 inelastic planar disks in 64 / 512 independent bounded tables. Radius 0.0625 scene units, table area 1.5, area occupancy 13.09%, initial velocity components vx in [-0.125,0.625], vy=±0.125. Initial pairs have a positive gap. Tables are separated by four units; world extents are 29.5×29 and 125.5×61, respectively. These are idealized unforced confined-disk scenes, not commercial pool material, one connected 8K island, or arbitrary cross-table interaction. The existing all-object isolation certificate and full relevant-pair checks qualify that separation.

| Recorded scenario | Small pool | Medium independent islands | Large distributed disks |
|---|---:|---:|---:|
| Result | **FAIL, stopped immediately** | Functional 30-s PASS | Functional 30-s PASS |
| N / wall seconds / simulated seconds | 16 / 3.1611 / 31.8125 | 1,024 / 30.0112 / 6.90625 | 8,192 / 30.0190 / 6.49219 |
| Accepted / unexpected rejected ticks | 4,072 / 1 | 884 / 0 | 831 / 0 |
| Accepted ticks/s, verification-inclusive | 1,288.15 (partial only) | 29.46 | 27.68 |
| Contact-bearing accepted ticks | 196 (4.81%) | 879 (99.43%) | 826 (99.40%) |
| Contact observations across ticks | 511 | 1,312,096 | 9,615,537 |
| Peak contacts / islands / largest island | 18 / 3 / 15 | 2,048 / 512 / 16 | 16,384 / 4,096 / 16 |
| Maximum actual solved bodies in one tick | 15 | 1,024 | 8,192 |
| GPU tick p50 / p95 / p99, ms | 0.2605 / 0.40925 / 0.84425 | 7.2235 / 10.6915 / 15.4825 | 4.72575 / 11.76475 / 17.65475 |
| Worst observed GPU tick, ms | 2.10975 | 58.26875 | **220.1675** |
| CPU queue-submit p50 / p95 / p99, us | 13.2 / 29.1 / 44 | 129.5 / 198.7 / 435.8 | 123.2 / 192.8 / 418.0 |
| GPU-fence blocking p50, ms | 0.3039 | 7.9319 | 5.2449 |
| Outer verification p50, ms | 0.1687 | 26.2796 | 29.5558 |
| Tracked committed GPU bytes, constant | 1,638,400 | 5,505,024 | 35,979,264 |
| Runtime buffer allocations, constant | 25 | 23 | 23 |
| Rollback / resource cleanup | Actual failed tick PASS / PASS | Separate injected rejection PASS / PASS | Separate injected rejection PASS / PASS |

Contact observations are a sum across ticks, not unique pairs. Counts are actual GPU outputs with mandatory publication/guard validation. The two distributed runs execute independent CPU full-contact/KKT, impulse reconstruction, pair coverage, identity, island/color and energy/momentum checks **every tick**. CPU references cover 7,712,768 body-ticks in those two runs. There are no unreported rejected ticks or validation failures there. The small run reuses the pool analytical collision/energy regressions and checks every body's finite state, identity, separation, table bounds and full mechanical energy including rolling on every tick. Its GPU KKT/impulse/position/energy checks remain enabled. **An independent per-contact CPU pool KKT oracle is not implemented**; its empty oracle struct is not evidence of zero residual. The corrected pool CSV leaves that residual blank.

**Small-scene failure:** On zero-based attempt tick **4,072**, after nine rest-gated shots, the GPU reports error **32**, publishes zero bodies and preserves the complete prior SoA and retained rolling-state SHA-256. Last accepted energy and rejected-state energy are identical (0.0729200993659801). The tick reports two contacts, one two-body island and max 19 solver iterations, below the 4,096 limit. Error 32 is shared by contact KKT validation, impulse reconstruction, position correction and penetration validation (`physics.hlsl`); the raw capture does not retain the pool diagnostic subcode/contact state needed to isolate its origin. **Do not label it a proven geometry defect or convergence exhaustion.** The safe rejection/rollback works, but the pool scenario fails sustained reliability and is not retried or tuned. The post-session injected probe is not run after that failure; the actual rejection rollback is recorded separately. Fixing this physics failure is a subsequent scoped task.

**Memory and latency boundaries:** Tracked commitment and allocation count are exactly constant at every measured tick in all three scenarios. Each cleanup returns to the 65,536-byte runtime context, zero retired bytes and zero reported validation errors; measured non-context allocations are retired. These are runtime buffer counts, not a native D3D12 allocator census. DXGI Budget and CurrentUsage are recorded per tick. CurrentUsage is the application's process-wide video-memory usage, not other processes' memory or a per-buffer residency measurement ([Microsoft API definition](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_4/ns-dxgi1_4-dxgi_query_video_memory_info)); this clarifies the earlier broad P7 wording without changing its evidence. Native debug-layer/GPU-based validation was not enabled during timing.

Finite observed maxima and fixed work/capacity bounds do **not** establish stationary latency or hard deadlines. Five-second windows show medium GPU p50 0.7965→7.8565 ms and large 1.3295→9.03025 ms as the scenes evolve. The runs contain 412 / 288 GPU ticks above 7.8125 ms, including the 220.1675-ms large outlier. No leak is observed, but sustained latency qualification is **UNVERIFIED**; do not call these 128-Hz operating envelopes. Discovery is the largest median GPU phase (4.530 / 2.5515 ms), followed by graph work (1.098 / 0.954 ms); solver phase medians are only 0.15125 / 0.14975 ms. Outer CPU full-state/reference verification dominates the measured end-to-end cadence. These are timestamp intervals, not hardware counter, cache-miss or preemption attribution. No optimization was attempted.

**Decision and limited-release blockers:** The largest **tested, functionally reliable** case is **8,192 actual interacting disks**, with 831 accepted ticks at 27.68 verification-inclusive ticks/s for this 30-wall-second distributed, maximum-16-body-island scene. It is not a general topology, real-time, 30-simulated-second or larger-N guarantee. The overall P8 outcome is **LIMITED / SMALL POOL FAIL**. Release blockers include the pool validation rejection and missing failure subcode, latency drift/outliers and unmeasured production-only cadence, lack of broader topology/duration/device repetition, deferred large-island G5 debt, GPU-02 and physical recovery qualifications. Keep G5 deferred and G6 NOT QUALIFIED. Next: capture the already reported pool validation subcode/contact state in a separate targeted diagnostic task; do not restart solver optimization or reinterpret safe rejection as successful physics.

**Reproduction/evidence:** From a fresh isolated current-main-based checkout: `python run_g6_p8.py` builds/reuses verified artifacts and runs one serialized CLI batch; it refuses overwriting evidence. `python verify_g6_p8.py` is offline only. `python -m unittest test_g6_p8 -v` checks evidence logic. `G6-P8-Sustained-Physics-20261019.zip` contains the complete living architecture, CLI measurement source/tests, exact commands, 5,788 raw tick JSONL records plus CSV, original and corrected consolidated JSON, per-window/stage/memory distributions, process/build logs, 33 compiled-source hashes, executable/tool and 85 DXIL hashes. Offline summary fixes did not rerun or replace raw GPU results.

**Independent uploaded ZIP/GitHub audit (2026-10-19):** The uploaded `G6-P8-Sustained-Physics-20261019.zip` (42 entries) passes CRC and **41/41** manifest SHA-256 file checks; there are no unlisted entries. The included offline handoff verifier was independently executed and returned `PASS 41 file hashes; 5788 ticks reconciled; pool FAIL preserved, distributed PASS scoped; G6 NOT QUALIFIED`. All **seven** source/document Git blobs in the archive independently match the pushed isolated branch revision `961e32ebe10746cf9d8635c9b169769d7237fc5c`, parent `b4754a1606c2e7d3ca42f92c0d5b462b82544593`; it is **not merged** into primary branch production source. Independently recounted the raw JSONL: **4,073** pool attempts (**4,072 accepted + one unexpected error-32 rejection**), **884/884** medium accepted, **831/831** large accepted; **5,788 raw TICK records total / 5,787 accepted / one unexpected rejection**, plus **two distinct expected post-session injected rejection probes** in the passing distributed runs. The failed pool tick `tick=4072` reports **2 contacts, one 2-body island, max 19 per-island solver iterations, no publication, rollback hash identical to previous accepted state**; nine rest-gated cue shots occurred before the failure. All 30-second distributed wall sessions have stable committed allocation and safe cleanup, while the pool stops after **3.161 seconds wall time** despite having advanced **31.8125 seconds simulated time**; this is a correctness failure, not a duration pass. Independently checked raw CPU submit/record p50/p95/p99 nearest-rank quantiles for all three cases against the corrected results: **18/18 values exact**. Both distributed cases preserve the mandatory GPU checks and use an **independent full-contact CPU verification every tick**; pool independent KKT is explicitly unavailable (the default empty verifier payload is not zero residual). **No independent Windows GPU execution** was performed here, and reported preservation of 354 original tracked hashes/dirty status is developer evidence. Runtime allocation counters are not a census of native D3D12 allocations. The rejected tick's flag `32` is a **shared** validation code for KKT/impulse/position/penetration paths; the precise predicate is **not recovered** from this archive. This audit **does not** turn the 8,192-disk 30-wall-second run at **27.68 verification-inclusive accepted ticks/s** into a real-time, sustained-latency or general-topology pass; GPU tick maxima **58.27 ms medium** and **220.17 ms large** and the evolving 5-second windows prohibit that conclusion. P7 GPU-02 and G5 remain deferred/unverified as previously decided.

### G6-P8a pool rejection localization — DIAGNOSIS VERIFIED / NOT FIXED (2026-10-19)

**Base and limits:** Start at current main `16a270ed3217ae0e4d2fc96f9ba6d0e8bf8955e6`; copy only the P8 `physics_main.zig`/`sustained_physics.zig` measurement branch from `g6-p8-sustained-qualification-20261019`. Preserve the complete current-main architecture record, the original workspace's 353 tracked hashes and dirty status, and original P8 evidence. No G5 experiment, solver/default/equation/tolerance change, GUI or display probe is performed. **G5 remains DEFERRED / NOT QUALIFIED; G6 remains NOT QUALIFIED; GPU-02 remains UNVERIFIED.**

#### Complete shared-error audit and failure-only capture

There are **six** direct `fail(32)` sites in the physics error domain, split into nine predicate subcodes. The earlier count of seven sites was imprecise; the source/contract test fixes the count. `spatial.hlsl` has two separate local scatter overflow `fail(32)` sites; `ph_append` forwards these as `1 | (spatial_error << 16)` (32 becomes 0x00200001), so they cannot produce the observed plain physics error 32. No untraced plain-32 solver path was found.

| Subcode | Predicate / failure path | Physics source |
|---|---|---|
| 1 | Normal projected KKT residual exceeds tolerance | `physics.hlsl:143` |
| 2 | Tangent projected KKT residual exceeds tolerance | Same original compound contact check |
| 3 | Negative or nonfinite normal impulse | Same contact check |
| 4 | Tangent impulse violates friction projection | Same contact check |
| 5 | Per-body impulse reconstruction exceeds bound; captures axis | `physics.hlsl:161` |
| 6 | Coincident pool positions during correction | `physics.hlsl:184` |
| 7 | Position correction fails its existing 64-pass criterion | `physics.hlsl:193` |
| 8 | Correction displacement exceeds existing cap | `physics.hlsl:196` |
| 9 | Post-correction candidate pair penetration exceeds bound | `physics.hlsl:198` |

`pool-failure-diagnostic.hlsl` adds a first-writer CAS latch and a 64-byte payload: subcode, tick, body/contact identifiers, detail/axis, **binary64** value, threshold and two auxiliary values, plus two raw words. The record uses existing spare pool bytes **448–511**, immediately after the Y-position array and below the 512-byte guard boundary. The generated shared `pool-schema.json`/`pool-layout.h` contract is version 2; the extension stays **768 bytes**, with no new GPU allocation or changed existing offsets. `ph_guards` initializes the latch once. Only an already failing predicate writes its payload, before the unchanged `fail(32)` call; no per-tick clearing or accepted-tick forensic readback is added. The atomic winner is the first recorded GPU failure, not a promised lowest contact ID or serialized lane order.

Diagnostics require `G6_POOL_FAILURE_DIAGNOSTICS=1` on the five affected shader entries. The default is **0**. All **85 default DXIL files are byte-identical to the unchanged control**, demonstrating that the default diagnostic path compiles out. The runner temporarily installs the five instrumented entries, records two repeats and restores verified default shaders in `finally`. The existing P8 test host saves raw source/trial/metadata/contact buffers **only after a failed, fence-complete tick**; normal accepted ticks retain the P8 path. Relevant contact inputs, impulses, body states and rolling state are retained for independent offline arithmetic.

#### Reproduction and exact predicate

One unchanged control and two serialized diagnostic repeats all reproduce zero-based attempt **4,072**, after the same nine rest-gated ±1.5-m/s cue shots at ticks **0, 288, 812, 1277, 1818, 2245, 2806, 3248, 3822**. Every one of the **4,073** recorded accepted/rejected state hashes in each run matches the original P8 run. Six final CPU diagnostic/layout/coverage/witness tests pass. The scenario processes deliberately exit 1 because they reproduce the existing rejected tick; the diagnostic verification is PASS and never relabels this as a physics pass.

Both diagnostic records identify **subcode 1, normal contact KKT residual**, contact record **1**, stable ball ID **7**, generation **1**, versus right-wall ID **17 = N+1**. The other contact is ball 7 versus ball 8. Trial body 7 is at `(2.5110435485839844, 0.6317485570907593)` with velocity `(0.048828125, -0.11729887127876282)` and yaw `4.104947566986084`. Its free velocity/yaw are all exactly zero. Normal/tangent impulses are `0.2066767964114747` / `-0.012403889412663788`; the friction bound is `0.03100152069361091`. No invalid-input rejection is present. The contact check precedes body checks and positional correction (`physics.c:91`); the position stage is stopped after this failure, so it did not originate in position correction or pair penetration.

| Independently reconstructed quantity | Exact captured/recomputed value |
|---|---:|
| FP32 table-width input | 2.5399999618530273 |
| FP32 radius input | 0.028574999421834946 |
| `append()` rail gap, FP32 intermediate subtraction (`physics.hlsl:86`) | 0.0003814697265625 |
| `geometry()` rail gap, FP64 subtraction (`physics.hlsl:141`) | 0.00038141384720802307 |
| Difference in gap | 5.587935447692871e-08 |
| Stored solver target from FP32 gap (`physics.hlsl:87`) | -0.048828125 |
| Validator target from FP64 gap | -0.04882097244262695 |
| Actual relative normal velocity | -0.048828125 |
| Residual against stored solver target | **0 exactly** |
| Residual against independently reconstructed target | **7.152557373046875e-06** |
| Unchanged KKT threshold | **7.271219886650902e-07** |
| Residual / threshold | **9.836805219132655** |

The input is finite and geometrically valid, with positive initial rail gap. With zero free normal velocity, restitution is not the active target branch: the separation/dt target applies. The solver exactly satisfies its stored target. `append()` first rounds `(width - radius)` in FP32, then subtracts X; `geometry()` performs those subtractions in FP64 from the same stored FP32 inputs. The gap difference divided by dt=1/128 is **exactly the measured normal residual**. Independent offline binary32 rounding plus binary64 reconstruction matches the GPU value and limit bit-for-bit. This proves a **pool rail target representation inconsistency**, not a guessed convergence, bad-input, or position-correction problem. The rejected tick reports max 19 solver iterations, below 4,096; increasing iterations cannot make two inconsistent targets equal. No solver optimization is justified by this failure.

#### State integrity and decision

All three replays preserve the last accepted state hash:

`1d219f358287d6dc0853c59c74805d8ca4a1c90fd5ea995f7287d4c256919d39`

It covers the full capacity-32 SoA including padding and the G1 source guard, plus the retained current rolling arrays. Publication reports **zero** and the last accepted/rejected hashes are identical. The binary source dump uses `ph_read(0)`, which excludes the G1 source guard; offline verification reconstructs the declared 64 `0xbaadc0de` guard words and requires the full digest to equal **both live hashes**, without pretending that those guard bytes were directly dumped. Working trial/contact/metadata bytes are allowed to change; they are not part of committed simulation state. Each cleanup returns to 65,536 context bytes, zero retired bytes and zero reported validation errors. Default shaders are restored. Native debug-layer validation was not enabled, and no performance conclusion is drawn from diagnostic timings.

**Decision: LOCALIZATION PASS; ORIGINAL PHYSICS FAILURE REMAINS OPEN.** Stop GPU reproduction after these two diagnostic repeats. Do not suppress subcode 1, widen KKT tolerance, accept the rejected state, alter solver work limits or retry G5 policies. The smallest supported correction to evaluate **in a separate follow-up** is to construct each pool rail gap in binary64 from the stored FP32 inputs before `poolTarget`, consistently with `geometry()`, then retain the existing final target storage and acceptance criteria. That is an arithmetic-consistency proposal, **not an applied fix**; all four rail directions, near-boundary values, impacts/persistent contacts, energy, rolling rollback and the nine-shot sequence still need targeted validation before retention. No solver mathematics was changed in this task.

**Reproduction/evidence:** Fresh isolated checkout at this breakpoint. Record the unchanged control with the P8 harness before applying shader instrumentation (`python run_p8a_control.py`); then use the current source `python run_g6_p8a.py` for verified/cached compilation and two serialized diagnostic runs. `python analyze_pool_fault.py`, `python -m unittest test_pool_diagnostic -v` and `python verify_g6_p8a.py` are offline only. `G6-P8a-Pool-Validation-20261019.zip` includes exact phased commands, original/control/diagnostic JSONL, source/trial/meta/contact dumps, decoded JSON/CSV, complete architecture, source/tool/host/shader hashes and a read-only verifier. The existing control must remain the pre-instrumentation reference; the reproduction guide explains how to create it from the recorded main base plus the P8 harness. No broad campaign or additional GPU run follows localization. A final blank-line whitespace cleanup was rebuilt without GPU execution: the host, all 85 default shaders and all five diagnostic shader binaries match the tested outputs byte-for-byte. The exact pre-cleanup shader source, source hashes and rebuild commands are retained in format-rebuild.json.

**Independent handoff/precision audit (2026-10-19):** Uploaded `G6-P8a-Pool-Validation-20261019.zip` passed CRC and all **217/217** listed SHA-256 payload hashes across **218** ZIP entries; there were **zero** missing or unlisted entries. The supplied offline `verify_handoff.py` returned **PASS**, with no GPU/Windows commands run. All **12** changed source/document Git blob identities match published branch `g6-p8a-pool-validation-20261019` revision `2db61f69b9dc84e02e8109792110caa1c415149e`; branch lineage includes main base `16a270ed3217ae0e4d2fc96f9ba6d0e8bf8955e6`. Independently parsed all four archived JSONL histories (original P8 + unchanged control + two diagnostic repeats): **4,073 attempts each, 4,072 accepted + one tick-4,072 flag-32 rejection, nine identical shot ticks, all 4,073 committed `state_hash` values byte-equal to the original in each replay**. Both diagnostic runs report first captured subcode **1**, body **7** generation **1**, right rail **17**, normal KKT residual **7.152557373046875e-06**, tolerance **7.271219886650902e-07**, and no publication. Independent IEEE754 binary32/binary64 arithmetic confirms the gap difference **5.587935447692871e-08**; multiplying by the fixed 128-Hz step rate produces **exactly** the observed normal residual, ratio **9.836805219132655** to the unchanged threshold. The solver's stored target residual is exactly zero. Post-failure accepted state and rolling-state hashes remain unchanged and cleanup succeeds; the original G1 source guard is reconstructed for the offline full-state witness, **not directly dumped** by `ph_read(0)`. The recorded control and two diagnostic processes intentionally **exit nonzero to indicate unchanged physics rejection**—they are NOT physics passes. Six CPU evidence tests and the recorded **85 byte-identical default DXIL** outputs support the isolation contract, but native GPU tests were **not independently rerun** and normal DXIL outputs were not regenerated here. **No repair, softened KKT tolerance, new solver policy, or G5 work was authorized or applied**. The P8 sustained-workload and P7 display limits remain unresolved.

## 15. Breakpoints and qualification record

A **breakpoint** is a formal gate close, a gate reopen, a changed system contract, a release candidate, or a validated performance decision. An ordinary small code edit is **not** a breakpoint.

| Breakpoint | Scope | State as of this record | Evidence / open issue |
|---|---|---|---|
| **G0** | Capacity limits and legal GPU resource plans | **Passed as planning** | No large-execution performance claim. |
| **G1** | ECS, storage layout, lifetime, growth | **Passed in historical scoped tests** | SoA selected; 10M storage workload measured. |
| **G2** | Spatial search and contacts | **Passed in historical scoped tests** | Hash selected; contact construction verified. |
| **G3** | Integrated evolving physics | **Scoped results available** | Large connected workloads exposed severe cost. |
| **G4** | Graphics, overlap, playable viewer | **Conditional GO; P7 real-window application PASS; GPU-02 UNVERIFIED** | Four matched windowed collision-bearing runs plus two controlled API-removal cases pass in recorded local evidence. PresentMon 2.6.0 ETW capture denied (exit 6); zero displayed image/latency samples and no OS scanout correlation. |
| **G5** | Large islands, convergence, robust solver performance | **DEFERRED — CURRENT WORKSTREAM CLOSED; NOT QUALIFIED** | Algorithmic Anderson candidate rejected: eight formerly converging configurations lost convergence. Retained shader restored; large connected-island latency/convergence remains an accepted *development risk*, not a gate pass. Restart only on a demonstrated workload need or a separately authorized architecture prototype. |
| **G6** | Reproduce applicable gates, approve an engine foundation | **P8b CORRECTED / MERGED; P9 BLOCKED on native state repeatability; formal G6 NOT QUALIFIED** | Four fresh 30-second pool/1K sessions pass physics validation and cleanup. 1K A/A first differs at tick32; targeted traces prove identical input/contact sets but different color schedules and FP32 velocities. 8K/lifecycle runs stopped. G5 DEFERRED; GPU-02 UNVERIFIED. |

### Current G5 decision (2026-10-19)

**Finding:** The large-chain bottleneck is substantially algorithmic: the verified unit-mass 1,024-body chain has a poorly conditioned normal operator (about **424,971**) and the deterministic post-restart residual envelope contracts by about **0.995 per sweep**. The bounded depth-one Anderson trial greatly reduced iterations on some branching/dense/oblique fixtures but introduced **eight previously passing topology/policy convergence failures**, including policy-4 chains of 256 and 1,024 bodies. On chain-1,024, the candidate had **KKT ratio 107.98** and was correctly rejected/rolled back. Lower timing for this failed attempt is not a simulation speedup. Control accepted **115/120**, candidate **93/120**; all **27** candidate rejections verified rollback. The retained shader was restored exactly.

**Decision: G5 DEFERRED / CURRENT OPTIMIZATION WORKSTREAM CLOSED — NOT QUALIFIED.** No more G5 tuning or GPU micro-optimization sweeps are scheduled. Preserve the previously retained small safe optimizations, production policy **1**, opt-in policy **4**, `G5_BODY_CACHE=0`, `G5_REUSE_MEASURE_BODIES=1`, `G5_SKIP_OVERWRITTEN_RESIDUAL=1`, and `G5_DETERMINISTIC_MEASURE=0` by default. The test-only O(C²) scheduler and rejected Anderson experiment must never be promoted by default.

**Next work:** Shift to independently valuable GPU engine tasks: strict generation-state isolation, resource/scheduler design, public host API, recovery and error handling, representative smaller/scattered-island workflows, and missing G4 real-display verification when display claims matter. **G6 scoping/preparation may begin** with a written, limited application envelope, but **formal G6 foundation qualification is not authorized** by deferring G5. Revisit G5 only when a target workload and a potentially material architectural alternative justify it. Do not claim large-connected-island real-time throughput, million-body full physics or G5 pass.

**Evidence:** `G5-Algorithmic-Convergence-20261019.zip`, 2026-10-19, evidence branch `g5-convergence-anderson-20261019`, revision `a147f6bf265bc82060107358cd41157e38d371c2`. ZIP CRC and 2,159 file hashes verified; 240 recorded Windows runs, 20 residual probes, independent statuses/invariant/rollback checks and 46/49 unit-test logs inspected. No independent Windows GPU test or production shader merge was performed for this documentation decision.

### G6 preparation decision before P5 integration (2026-10-19)

**Finding:** P1–P3 source and playable renderer were integrated into `main` and the playable branch in PRs #1/#2, preserving both histories and the complete architecture record. The new P4 experiment is **separate**: it compiles the real offscreen renderer to lease the last accepted generation while a newer compute tick is pending and validates the newer tick at ordered retirement. A native gated-producer test proved two GPU draws from generation 0 while newer work was blocked (ages 1/2) with successful later release, rejection/rollback, lease exhaustion and delayed cancellation. The Windows evidence records 11 passed tests (six freshly executed, five unchanged-binary reuses). In one matched 32-sample-per-arm headless timing set, median CPU acceptance blocking fell **366.5→0 μs** and CPU handoff **751.3→347.0 μs**, but physics GPU tick increased **602.5→786.5 μs**, renderer GPU time **16.384→22.528 μs**, and accepted snapshot age rose from **zero to one tick**.

**Decision: G6-P4 LOCAL PREPARATION PASS / DO NOT CLAIM THROUGHPUT IMPROVEMENT; FORMAL G6 NOT QUALIFIED.** Retain the correct nonblocking mechanism on the independent `g6-p4-nonblocking-consumer-20261019` branch; do not confuse it with a tested merged `main` build. Ordinary frames may use a previous accepted immutable generation; command acknowledgment still requires matching-tick acceptance and may block. No physics/shader change or additional GPU allocation is established; full frame throughput and interactive display are not. G5 stays **DEFERRED / NOT QUALIFIED**; physical device-loss recovery, GPU-02 displayed FPS and G6 foundation signoff remain unverified.

**Next action:** First reconcile P4's post-P3 branch onto the current **integrated main** source history without replacing the complete architecture doc, and run a limited Windows proof of actual renderer lease correctness and accepted-state age/cost on that merged code. Then investigate a **bounded device-loss/teardown/reinitialization contract** separately. Model injected faults accurately, handle invalid fences and held consumer leases, and do not claim device-removal recovery without actual device-removal/recreation tests. Avoid further G5/solver optimization campaigns.

**Evidence:** `G6-P4-Nonblocking-Consumer-20261019.zip`, commit `aa7d77cdfcef0efe777539aa876d2a5b05cb7ba3`; 149/149 archive hash checks and offline verifier pass; recorded 11 PASS test entries, control/candidate EXE hashes and all 14 raw-timing reconciliations checked; no independent Windows GPU run during this GitHub documentation update.

### G6 preparation decision before P6 — P5 (2026-10-19)

P4 source is integrated with current main through a history-preserving merge and tested in one corrected bounded Windows headless comparison. Both modes preserve immutable accepted snapshots, command acknowledgement, fences, ownership, rollback and backpressure. Nonblocking is an explicit `--nonblocking 1` option; blocking (`0`) remains the application default. Twenty final checks pass, eight reused on unchanged inputs. See the P5 technical decision for measured throughput, increased render GPU intervals and one-tick ordinary snapshot age; this is not G6 qualification or displayed FPS. Physical device-loss detection, safe teardown and recovery-boundary validation are the next separate task. G5 remains deferred.

### Previous G6 preparation decision — P6 (2026-10-19)

Sticky failed contexts, checked bounded teardown and explicit new-scene recreation pass 16 fresh final headless processes. Two cases executed native D3D12 RemoveDevice and recreation; four injected API failure points and one controlled held-consumer timeout preserved unsafe-to-release resources. Recreated contexts executed both real render modes and rejected old identities. This proves controlled API-removal boundaries, not physical hardware/driver recovery, checkpoint continuation or GUI restoration. P5 blocking default and opt-in nonblocking behavior remain. G5 DEFERRED / NOT QUALIFIED; formal G6 NOT QUALIFIED. Preserve the tested source and qualify broader recovery requirements separately.

### Previous G6 preparation decision — P7 (2026-10-19)

**Finding:** The isolated P7 branch instruments the real windowed 16-ball renderer's submit, DXGI Present-return and GPU-retirement events without inferring OS displayed frames. A single 21.75-second Windows session reports four normal ABBA application runs and two controlled API removal/checked teardown runs passing. In each normal run, 298 frames complete and 286 ticks simulate, including 137 contact-bearing ticks with up to 18 contacts and a 15-body island. Pooling the two normal runs per mode (596 frames/572 ticks), GPU physics p50 is **0.2905 ms blocking / 0.2910 ms opt-in nonblocking**; CPU acceptance wait p50 **7.3644 / 0 ms**, but CPU loop-body p95 **8.5396 / 16.1984 ms** and snapshot-age p95 **0 / 2 ticks**. These are application metrics, not display FPS. A real local EDID-valid 2560×1440@120Hz HDMI target was identified, but PresentMon **exit 6 / ETW access denied** meant zero native OS displayed-image events, dropped/repeat counts or per-image display latency samples. Archive CRC, all 78 file hashes, 13 pushed Git source hashes, all six raw application cases and 16 pooled quantile groups were independently verified; Windows execution was not rerun.

**Decision: G6-P7 LOCAL APPLICATION PASS; GPU-02 and formal G6 NOT QUALIFIED.** Keep P7 telemetry/test instrumentation on its isolated branch pending a scoped integration decision; no P7 source, solver defaults or shader changes were merged by this documentation update. Blocking remains the renderer default. Controlled D3D12 RemoveDevice during a real windowed session proves stopped submissions and checked teardown, not physical hardware/TDR recovery or GUI/swapchain recreation. G5 remains **DEFERRED / NOT QUALIFIED**.

**Next:** Require an **authorized local-console PresentMon/ETW capture** (elevated Windows terminal or administrator-granted Performance Log Users membership with logoff/logon). Capture separate repeated blocking/nonblocking sessions, preserve trace loss diagnostics, capture version/hash, QPC timestamps, monitor configuration and actual per-image displayed/dropped/repeated events. Correlate by process/swapchain/image and known timestamp/ID domains; do not assume GetLastPresentCount equals ETW PresentId. Only then decide GPU-02 and the actual display-performance envelope. If tracing permission remains unavailable, park GPU-02 as **UNVERIFIED** and proceed independently to a short sustained small/multi-island workload envelope, without claiming displayed FPS. Physical photon/input-to-light latency needs separate optical equipment.

**Evidence:** Uploaded `G6-P7-Display-Qualification-20261019.zip`; code branch `g6-p7-display-qualification-20261019` at `0df58576a335364876b64f233f8fac30fea82571`. Includes six archived process logs and raw per-frame samples; five unit-test pass records; original Windows source/hash and workspace receipts; PresentMon 2.6.0 permission failure; independent ZIP/hash/raw-data check as in §11. No independent Windows GPU reproduction.

### Previous G6 preparation decision — P8 (2026-10-19)

**Finding:** Independent validation of the uploaded P8 archive and seven pushed Git blobs confirms 5,788 raw physics attempts: **5,787 accepted, one unexpected 16-ball pool rejection**, with two additional expected post-session negative probes. Medium **1,024** and large **8,192** disk workloads complete 30 **wall-clock** seconds with **884** and **831** accepted physics ticks, respectively, under a strict maximum **16-body connected island**, mandatory GPU validation and full-contact CPU reference verification. The verification-inclusive average rates are **29.46** and **27.68 accepted ticks/second**; large case advances just **6.49 seconds of simulated time**. The pool case rejects at attempt **4,072** (flag **32**, precise predicate unknown) after nine rest-gated shots, though state rollback and cleanup work. All tracked runtime commitments and allocation counts are constant. Medium/large GPU tick p50 values are **7.2235 / 4.72575 ms**, but 412/884 and 288/831 GPU ticks exceed the fixed **7.8125 ms** step budget, with large max **220.1675 ms** and strong positive latency drift over successive 5-second windows. CPU reference verification/readback dominates end-to-end measured cadence; production-only throughput is not isolated.

**Decision: G6-P8 LIMITED / SMALL POOL FAIL; FORMAL G6 NOT QUALIFIED.** The 8,192-disk independent-island scene is the largest **functionally reliable tested** workload for this limited sample, not a qualified real-time, arbitrary-topology or production release envelope. Record the safe rejection as correctness protection, **not** successful pool physics. Do not relax validation/KKT, silently dismiss the failure, infer its exact cause from shared error 32, or reopen deferred G5 solver optimization. Keep P8 benchmark/diagnostic source on the separate `g6-p8-sustained-qualification-20261019` branch; this documentation update does **not** merge experimental source. G5 remains **DEFERRED / NOT QUALIFIED**; P7's GPU-02 remains **UNVERIFIED** by user's request to move on.

**Next task:** A **targeted pool failure-subcode diagnostic**, without altering solver math/limits/default policies: identify each error-32 predicate in shader and GPU validation paths, add minimal failure-origin and offending contact/body/state capture **only on rejected ticks**, and write one deterministic CLI reproduction preserving the nine-shot history, last accepted snapshot, rejected candidate, and rollback. Repeat just enough to isolate the predicate (no general G5 campaign, GUI, ETW, or broad rebenchmark). Separately, before calling the 8,192-disk envelope real time, measure a representative production-only short sustained variant **without per-tick independent CPU full-contact oracle**, while retaining the mandatory GPU checks, and document latency outliers/drift rather than hiding them. Do not declare a general release until pool correctness and its intended sustained workload envelope pass.

**Evidence:** User-uploaded `G6-P8-Sustained-Physics-20261019.zip`; developer Windows commit `961e32ebe10746cf9d8635c9b169769d7237fc5c`. All 41 file hashes, seven published Git blobs, independent offline handoff checker, raw per-tick counters, and CPU timing quantiles verified. No Windows GPU commands independently rerun during this documentation review.

### Previous G6 preparation decision — P8a (2026-10-19)

**Finding:** In the deterministic nine-shot pool fixture, the unchanged P8 control plus two instrumented diagnostic replays all reject **attempt 4,072** after 4,072 accepted ticks. Each 4,073-entry state-hash series matches the original, and the last accepted state remains published on failure. The first-failure latch identifies **normal KKT subcode 1, ball 7 (generation 1) versus right rail 17, contact record 1**. The stored normal target satisfies the solver exactly, but the validator recomputes the rail gap in FP64. The contact generator rounded the intermediate right-wall gap in FP32: `0.0003814697265625` vs FP64 `0.00038141384720802307`. Difference `5.587935447692871e-08` / (1/128 second) equals measured KKT residual `7.152557373046875e-06`, which exceeds unchanged `7.271219886650902e-07` tolerance by **9.836805219×**. This is a deterministic **precision/target-representation inconsistency**, not contact solver convergence exhaustion. The pool error remains unfixed.

**Decision: G6-P8a LOCALIZATION PASS / PHYSICS FAILURE OPEN; FORMAL G6 NOT QUALIFIED.** The candidate branch adds **test-only** first-error diagnostics in previously spare pool-extension bytes; 85 default DXIL files remain unchanged and diagnostic shader binaries are restored in the recorded run. No solver mathematics, KKT thresholds, rollback, or production behavior changed. This review **only updates the living architecture**, not production source. G5 stays **DEFERRED / NOT QUALIFIED** and GPU-02 remains **UNVERIFIED** per decision to move on.

**Historical plan, now completed and merged:** The following P8b next-task instruction was written before the correction in PR #5. It is retained as an evidence chronology, not an outstanding issue. The accepted correction and latest P9 status are recorded below.

**Next task (P8b):** Apply only a **precision-consistency correction** for pool rail gap formation: evaluate all four rail gaps with FP64 subtraction from existing stored FP32 inputs before `poolTarget()`, aligning with the FP64 validation geometry while preserving existing final target precision, equations, KKT tolerance, solver work cap and rollback. Use one bounded nine-shot reproduction and near-boundary tests for each rail, stable persistence/impacts and energy/rolling; compare unchanged control, fault-reproducing diagnostic, and correction. Do **not** suppress the subcode, increase iterations, widen acceptance or run G5 optimization sweeps. Record raw accepted tick/hash history, no regression in non-pool fixtures, and any remaining failures. Only if P8b passes may another small sustained sample be used to establish a limited envelope; P9 host API and P10 release approval remain later decisions.

**Audit evidence:** `G6-P8a-Pool-Validation-20261019.zip`; revision `2db61f69b9dc84e02e8109792110caa1c415149e`. 218 ZIP entries/217 verified payload hashes; bundled offline verifier PASS; 12 exact published Git blob matches; original + control + two diagnostic sequences, all 4,073 state hashes and nine shot ticks identical, IEEE754 gap/residual independently recomputed. Recorded GPU execution is not independent Windows testing.

### Merged correction and integrated qualification — P8b/P9 (2026-10-19)

**P8b correction:** Main merge `e843a42` contains PR [#5](https://github.com/Cryosimorgh/GPU-physics-engine/pull/5), source correction `b74e1d0`, and self-contained rail-test follow-up `1f8ea74`. It uses FP64 subtraction on the stored FP32 rail operands before `poolTarget`, preserving final FP32 formats, independent geometry validation, solver equations, KKT limits, rollback and scheduling. Only default `ph_append` and `ph_walls` DXIL changed in the recorded P8b comparison. The original residual 7.152557373046875e-6 versus 7.271219886650902e-7 threshold remains a historical failure; the focused corrected GPU witness reports zero residual.

**Evidence boundary:** P8b completed three local 30-wall-second sessions with 25,680 / 25,602 / 25,749 accepted ticks, no unexpected rejection, matching full hashes throughout the 25,602-tick shared prefix, constant 1,638,400 committed bytes / 25 allocations, checked rollback and cleanup. These are recorded local P8b results, not fresh P9 execution. Archive SHA-256: `3af285838b9f30cec090ef6df8e5cc89b8c731da1333fbdf8a75b10e54e470fb`. History and the prior failed P8/P8a observations are retained.

**P9 fresh execution / BLOCKED:** One 600-second-bounded serialized batch on main `e843a42` stopped after 176.47 seconds at the first failed repeatability comparison. All executed child tests returned success: 19 workflow/rail/reducer unit tests, five existing CPU tests, seven existing headless pool cases, and four 30-wall-second sessions. The engine source, solver policy, math, tolerances and all 85 default shader hashes remain identical to the retained P8b build; there were zero compilation actions. No GUI was launched.

| Fresh case | Accepted ticks | GPU tick p50/p95/p99 (ms) | CPU record / queue submit / physics fence p50 (us) | GPU / API / verification-inclusive deadline misses |
|---|---:|---|---|---|
| Pool A, 16 bodies | 26,181 | 0.27075 / 0.29625 / 0.40175 | 224.1 / 21.2 / 319.0 | 0 / 13 / 52 |
| Pool B, 16 bodies | 26,434 | 0.27100 / 0.29625 / 0.40125 | 222.2 / 19.8 / 319.1 | 0 / 11 / 50 |
| Distributed A, 1,024 bodies | 935 | 1.68725 / 2.49025 / 2.54625 | 349.1 / 150.0 / 1515.4 | 1 / 1 / 935 |
| Distributed B, 1,024 bodies | 893 | 1.68075 / 2.49075 / 2.74450 | 347.2 / 152.0 / 1508.7 | 1 / 2 / 893 |

The fixed-step budget is the existing **7,812.5 us**, not a new threshold. GPU stamp39 follows `state_record_copy` (`physics.c:93-94`), so the immutable snapshot copy is included. CPU `blocking_us` is the physics fence wait (`physics.c:108`); it overlaps GPU execution and must not be added to GPU time. `verification_us` also includes extra synchronous readbacks/CPU oracle work and is not a hardware barrier counter. The 1K oracle costs approximately **25.57 / 25.61 ms median**, dominating measured cadence; discovery is the largest measured GPU stage. GPU worst ticks are **11.013 / 11.141 ms** at 1K. No optimization or speedup claim is made.

**Functional results and reproducibility boundary:** Both pool runs match all **26,181 shared tick hashes**, and 25,680 shared ticks match archived P8b. They retain 382 contact-bearing ticks, max 18 contacts and max 15-body islands each. Both 1K sessions pass independent per-tick contact coverage, KKT, energy and state checks, reaching max 2,048 contacts, 512 islands and max 16-body islands. Tracked commitments and allocations remain fixed: pool **1,638,400 bytes /25**, 1K **5,505,024 bytes /23**. Four post-session rejection probes preserve the accepted state; all four cleanups return to context-only memory with zero retired bytes and reported runtime errors. Fresh pool ownership/fence tests pass. This is not a rerun of the complete P1-P6 ownership/consumer/device suite.

**First failure, isolated without changing production:** The 1K A/A state hashes first differ at **tick32**, despite equal 640-contact sets, 512 two-body islands and independently valid KKT ratio **0.7272727**. Total iteration counts differ (2,520 versus 2,524). Two additional targeted **33-tick** traces with the unchanged executable prove identical physical inputs and exact contact/geometry sets, but **48 per-root color schedules differ**; precisely 48 x-velocity fields differ, all in those roots, by **4.76837158203125e-7 m/s**. There are zero telemetry-only field differences in those traces. `ph_contact_scatter` uses an atomic cursor (`physics.hlsl:121-127`, atomic at125); `ph_color` greedily follows that list (`physics.hlsl:130`). Different valid projection orders can stop at different tolerance-bounded endpoints before FP32 publication (`projected_solver.hlsl:177`, `physics.hlsl:205`). This is a native scheduling/repeatability limitation, not a newly relaxed KKT pass or a proven solver equation defect. Existing single-island canonical measurement mode is outside this multi-island/rail envelope and was not enabled or expanded. G5 was not resumed.

**Comparison and work not rerun:** Against identical pool tick indices, P8b GPU p50/p95/p99 is 269.5/295.0/406.5 us versus P9 270.75/296.75/406.75 us. The old P8 1K GPU p50 was 7.2235 ms versus 1.66325 ms across the matched first 884 P9 ticks, but their state/schedules differ and captures are not an exact-arithmetic controlled performance comparison. Do not call this an implementation speedup. The **8K P9 sessions, native consumer/publication/work-ownership/device cases and final generic CLI regression were NOT RUN** after the failure. Previous P8/P8b/P6 records stay explicitly archived evidence.

**Decision / proposed P10:** P9 is **BLOCKED / INCOMPLETE**, with fresh functional evidence through 1K and exact replay demonstrated only for the 16-ball scene. Resolve the bounded multi-island repeatability contract without relaxing KKT, changing equations or restarting G5 optimization; then resume the paused 8K and lifecycle qualification. Keep verification-inclusive cadence separate from a future production-path latency measurement. G5 remains **DEFERRED**, GPU-02 **UNVERIFIED**, and formal G6 **NOT QUALIFIED**. No release approval is issued.

**Local evidence:** `evidence/g6-p9/results.json`, `decision.json`, four full JSONL/CSV streams, the stopped-batch logs and two terminal trace exports under `isolation/`. Original worktree status/artifact hashes are unchanged. The handoff includes source, native commands, compiler/tool/output hashes, historical comparison inputs and a read-only verifier. An initial runner syntax typo was corrected before any test process ran; no failed physics execution was hidden.

## 16. Risks and work still required

**P10 scope note (2026-10-31):** Native 3D numerical validity is now independently
tested and is not blocked by P9 bitwise equality. Its bounded GO does not close
the historical G5/G6/display risks below. Three stress samples cover independent
pairs, not dense arbitrary graphs or sustained deadlines. Tensor rotation is
first order; broader energy-drift qualification and higher-order integration
remain future work. There is no 3D viewer, public world API, convex/mesh/joint or
terrain support in this slice. Memory/consumer limits and rejected-tick behavior
are explicit in the P10 section above.

1. **State publication and freshness:** P1–P6 source is integrated; P7 real-window testing on an isolated branch records correct command acknowledgment and fence ownership in both rendering modes. Blocking remains default; opt-in nonblocking gives accepted-state snapshot age **p95 two ticks** in normal actual-window tests, versus zero blocking. Measure real display age only when external correlated events exist; do not infer it from a successful Present.
2. **General island convergence — deferred G5 debt:** Policy 4 remains opt-in with limited, valid quick-sweep results; it is not qualified for sustained/general workloads. The rejected Anderson trial lost previously accepted configurations. Do not loosen KKT/rollback or describe G5 as passed; reopen only against an explicit large-island requirement and new algorithmic design.
3. **Large-island architectural limitation — parked:** The 1,024-body chain requires about 4,024 sweeps, with ~140 ms of solver execution in deterministic test conditions. Its settled chain operator is poorly conditioned (~424,971). Recent noise-aware micro-optimizations were inconclusive; a bounded Anderson method broke convergence. The serial O(C²) deterministic sorter remains measurement-only. Do not initiate further G5 experiments without an authorized performance target and a new architecture hypothesis.
4. **Scheduler and resource-management scope:** G6-P3 raises the bounded consumer extra dependency count to **five** for the actual renderer; the stale header comment was corrected at integration. The API stays CPU-owner-thread serialized with 64 task/lease entries and 32 producer dependencies. Queue/fence claims do not implement a general multi-producer scheduler or GPU core allocator.
5. **Display verification / external permission:** P7 confirms a real active EDID-valid 120-Hz HDMI target and a functioning actual-window swap chain, but **PresentMon 2.6.0 ETW tracing failed with access denied (exit 6)** under a medium-integrity account. There are **zero** OS displayed-frame/latency samples; screen refresh, Present return, GetLastPresentCount and GPU timestamps cannot close GPU-02. Obtain authorized ETW access and independently correlate actual displayed/dropped/repeated frames, otherwise leave the gate UNVERIFIED.
6. **Evidence and deterministic replay:** The isolated policy-4 baseline has been recovered with all 25 source hashes and a successful 80-run behavioral sweep. Historical and rebuilt CLI hashes differ and the comparison reports 156 numerical and 23 color-count differences. Track compiler/link inputs and exact revision, shader hashes, fixtures and GPU/driver context; do not claim byte-identical replay.
7. **G6 sustained execution and release envelope:** Historical P8 remains the only 8,192-body 30-second evidence; it has substantial GPU deadline misses and is not real-time qualified. Merged P8b corrects the pool rejection. Fresh P9 pool/1K runs pass their physics checks but fail overall bitwise repeatability at 1K tick32, so 8K and the remaining lifecycle cases were not rerun. CPU verification-inclusive 1K cadence is only 29.75-31.13 ticks/s and every interval misses dt=1/128. Keep functional correctness separate from real-time and production-only claims; no general release approval.
8. **16-ball pool precision inconsistency — CORRECTED / MERGED, historical failure preserved:** PR [#5](https://github.com/Cryosimorgh/GPU-physics-engine/pull/5), merged as `e843a42`, promotes stored pool rail operands to FP64 before subtraction in admission and append. Independent validation and solver limits are unchanged. P8a tick-4072 normal KKT failure and safe rollback remain recorded above. P8b local evidence passes 24 rail cases and three 30-second pool sessions (25,680 / 25,602 / 25,749 accepted ticks), with 25,602 identical shared hashes. This closes that defect, not formal G6 or a general real-time claim.

## 17. How to update this living document

On **each breakpoint**, update this file **in the same change** as the breakpoint decision. Do not create a parallel architecture report as the only record.

Required update procedure:

1. Identify the breakpoint name, code revision, and date.
2. Update the affected technical sections if behavior or design changed.
3. Mark each claim as implemented, measured, experimental, conditionally accepted, or planned.
4. Add measured workload, hardware, sample count, and a link or path to evidence. If evidence stays local, say so.
5. Update the qualification table and the active risks. Retain failed results and prior decisions.
6. Add one short entry to the change log below.
7. Commit the document with the related code, or in the same breakpoint documentation commit. A gate is not closed if this step is missing.

For routine small fixes, update the relevant existing paragraph only if the technical contract changes. Do **not** run a full test campaign or rewrite the entire record to change a sentence.

### Breakpoint entry template

```text
Date and breakpoint:
Revision / branch:
Change:
Why it matters:
Evidence: fixture, hardware, samples, exact file/URL
Result: PASS / CONDITIONAL / FAIL / UNVERIFIED
Known limits:
Next action:
```

### Change log

| Date | Breakpoint | Record update |
|---|---|---|
| 2026-11-02 | G7 reference motion / connected solver / accepted-state smoothing | Native gravity trough, GPU partial admissions, active-colored solver with unchanged final checks, live achieved-rate display. 512/1K reference 3200 ticks and six native tests pass. Dense frictional trials retained; PR draft. |
| 2026-11-02 | G7 native application / bounded local hardware evidence | Native instanced perspective renderer, accepted GPU lease/copy bridge, cube/belts and invariant witnesses; 512/1K cases and lifecycle pass. Radial stress unsupported; PR #9 draft, acceptance open. G5/G6 unchanged. |
| 2026-11-02 | P10 hardware evidence audit - bounded correctness GO, final-head integration conditional | 135 checksums and 28 source hashes verified; all 9 gates PASS at ed618f9 on RTX 4070 Ti SUPER. Original evidence retained. No physics changes. Full sweep and CI required on final commit before merge. |
| 2026-10-31 | P10 native 3D foundation — bounded GO | Added tensor/quaternion 3D GPU sphere/plane dynamics, immutable publication and real delayed-reader proof. Seven native groups, all three stress scales and unchanged full 2D regressions pass. Numerical native validity required; bitwise replay remains unqualified. Formal G6/release remains not qualified. |
| 2026-10-31 | P10 full native Windows attempt — NO-GO / no suitable D3D12 compute adapter | Source 510192f, 17 CPU-only PASS, 9 shaders and DLL compiled. Empty authored world fails D3D12 context/admission on Hyper-V Video; 16/1K, native oracle/replay, pool/rail and 10K/100K/1M NOT RUN. Immutable Actions artifact 13053607373, SHA-256 retained; PR #8 unmerged. |
| 2026-10-31 | P10 PR #8 adversarial qualification follow-up — NO-GO pending hardware GPU | Fail-closed candidate discard and capacity migration safety, async-close tests, replay field coverage and unique run evidence added; no D3D12 hardware qualification or physics performance evidence. Keep PR draft/unmerged. |
| 2026-10-31 | P10 application-facing headless core branch — NO-GO pending native execution | Staged accepted-state-safe GPU edits, typed world handles, fixed-step async control, leases, ordered numerical replay and CLI regression plan implemented on a dedicated branch. No new Windows/D3D12 run or performance qualification reported. P8b MERGED, P9 INCOMPLETE, G5 deferred, GPU-02 unverified, G6 NOT QUALIFIED. |
| 2026-10-19 | G6-P8b merged correction / P9 BLOCKED on repeatability | PR #5 merged at e843a42; P8/P8a failed evidence retained. P9 records four functionally passing 30-second sessions, but stops at 1K tick32 repeatability failure; two short traces localize atomic scatter/color-order variation. 8K and remaining lifecycle checks NOT RUN. G5 deferred, GPU-02 unverified, G6 not qualified. |
| 2026-10-19 | G6-P8a pool KKT failure root cause — LOCALIZATION PASS / PHYSICS NOT FIXED | Verified 217 ZIP payload hashes, 12 pushed Git blob IDs and offline verifier; original P8, unmodified control and two diagnostics have 4,073 identical state hashes each, nine shots, and matching tick-4,072 rejection/rollback. Subcode 1 = ball 7/right rail normal KKT. Independently reproduced FP32 vs FP64 gap difference times 128 exactly equals residual 7.152557373046875e-06 (9.8368× limit). No solver/production fix, G5 deferred, P8 small pool still fails, G6 unqualified. |
| 2026-10-19 | G6-P8 sustained physics external audit — LIMITED / POOL FAIL | Independently verified 41 ZIP checks, 7 pushed Git blobs and 5,788 raw attempts (5,787 accepted, one shared-error-32 pool rejection). Medium/large 30-wall-second runs accept 884/831 ticks (1,024/8,192 disks in max-16-body islands), with stable tracked memory and checked rollback, but CPU-oracle overhead, GPU drift and 220.17-ms worst tick prohibit real-time claims. Pool 9-shot sequence fails at attempt 4,072; exact subvalidator unknown. G5 deferred, GPU-02 unverified, G6 not qualified. |
| 2026-10-19 | G6-P7 real viewer/display attempt — LOCAL APPLICATION PASS / GPU-02 UNVERIFIED | Verified archive CRC, 78 hashes, 13 source blobs matching isolated Git branch, six archived actual-window cases and all 16 pooled raw quantile groups. Four normal ABBA cases exercise 298 frames/286 ticks each with 137 contact-bearing ticks, and two controlled API removal cases shut down safely. Actual local HDMI/120 Hz verified but PresentMon ETW access denied (exit 6), zero OS displayed-image/latency samples. P7 source not promoted; G5 deferred, G6 not qualified. |
| 2026-10-19 | G6-P6 external handoff audit — VERIFIED / NOT G6 QUALIFIED | Verified all 210 ZIP payload hashes and the offline verifier, 16 fresh PASS recorded processes, 8 lifecycle cases (2 controlled real D3D12 API removals), 18 published source/blob IDs and 85 unchanged DXIL outputs. Original workspace preservation is developer-reported; no reviewer Windows execution or physical hardware/TDR recovery. G5 deferred, G6 not qualified. |
| 2026-10-19 | G6-P6 device failure/teardown — LOCAL PASS, PHYSICAL RECOVERY UNVERIFIED | Added sticky failed states, proof-gated checked teardown, CPU owner ordering and cross-context handle generations. Sixteen fresh final headless runs pass; two actual controlled RemoveDevice cases recreate fresh GPU scenes and execute both render modes. No physical fault, checkpoint or GUI recovery claim. All 85 DXIL unchanged; G5 deferred, G6 not qualified. |
| 2026-10-19 | G6-P5 external ZIP and merged-main audit — VERIFIED / NO NEW GATE PASS | Independently checked all 193 archive hashes, 16 integrated source/document Git blobs, exact two-parent merge, 32 timing summaries and four pooled throughput groups. The 20 PASS records include 12 fresh and eight unchanged-input reuses. Integrated nonblocking remains optional; G5 deferred, G6 not qualified, GPU-02/device removal unverified. |
| 2026-10-19 | G6-P5 current-main/P4 integration — SELECTABLE, BLOCKING DEFAULT | Preserved both histories and full main architecture; 20 PASS records (12 fresh/8 unchanged-input reuse). Measured complete throughput +7.5% idle / +24.7% short pool motion; render intervals increase, snapshot age +1, no allocation growth. Fixed stale-command benchmark fixture without weakening validation. G5 deferred, G6 not qualified; device-loss boundaries are next. |
| 2026-10-18 | Baseline document | Established the technical inventory, G0–G5 history, evidence labels, known risks, and mandatory breakpoint update process. No new gate was approved by this documentation commit. |
| 2026-10-18 | G5 adaptive-solver decision — FAIL | Reviewed 60 CLI runs and matching JSON/CSV summary. The adaptive policy converged in 16/20 runs but failed the 256- and 1,024-body chains. It was rejected; the previous policy remains the local baseline, and G5 stays open. |
| 2026-10-18 | G5 bounded-restart candidate — CONDITIONAL | Reviewed 60 headless GPU runs and six diagnostics. Policy 3 converged in 20/20 local attempts, but 256/1,024-body chains and several branching/oblique networks suffered performance penalties. Production remains unchanged; G5 remains unqualified. |
| 2026-10-18 | G5 residual-gated restart — OPT-IN RETAIN | Audited 80 short GPU timing runs, 10 trace checks and 17 reported sweep unit tests. Policy 4 converged in 20/20 and lowered aggregate GPU p50 sum by 13.5% relative to policy 3, but remained slow on large chains. Production policy 1 unchanged; G5 unqualified. |
| 2026-10-18 | G5 shared-body-cache experiment — REJECT | Audited 100 CLI timing trials, 22 probes, 22 unit tests and the HLSL source. 1,024-body GPU p50 improved 170.13→152.69 ms, but aggregate geometric mean worsened 4.25%. Hardware counter attribution is unverified. Default remains cache-off; G5 open. |
| 2026-10-18 | G5 baseline-recovery blocker — BLOCKED / PARTIAL RECOVERY | Local Codex run made no solver or GPU-test change after losing the policy-4 baseline. Exact 3.6 MB archive and workflow dependencies were found and SHA-verified, and a read-only recovery kit was made. Four source matches and Windows retest remain outstanding. |
| 2026-10-18 | G5 isolated baseline — RECOVERED / NOT QUALIFIED | Restored 25 source files and six workflow hashes; archived 33 passing workflow tests, an 80-run Windows sweep, and 74 accepted/six expected rejected trials. Policy 4 passed 20/20. Rebuilt CLI differs in SHA and the per-run record has 156 numerical differences, so exact replay remains unverified. |
| 2026-10-18 | G5 residual body-snapshot reuse — RETAIN LOCALLY | Audited a small HLSL change, static DXIL reductions, 200 control/candidate GPU trials and 33 unit tests. Retained after independent correctness checks and aggregate p50 improvements. 1,024-body GPU p50 167.33→162.99 ms, with individual fixture regressions and no formal G5 qualification. |
| 2026-10-18 | G5 skip overwritten residual scans — RETAIN LOCALLY | Audited a conditional skip before mandatory reconstructed-state residual checks. Reviewed 200 recorded headless timing trials, six traces, 34 final unit tests, matching JSON/CSV summaries and source hashes. Policy-4 chain-1,024 p50 165.61→155.86 ms; 4,026 iterations unchanged. Broad geometric-mean gain only 0.28%. G5 remains unqualified. |
| 2026-10-19 | G5 early residual restart — REJECT / ROLLBACK | Audited 200 timed trials, 40 traces and 37 unit tests. Early policy-4 restarts saved 256 iterations on large chains, but its ten-fixture geometric-mean GPU p50 worsened 0.97%, failing the retention rule. Tested shader rolled back byte-for-byte; production policy 1 remains unchanged. |
| 2026-10-19 | G5 A/A repeatability — MEASURED / NO SOLVER CHANGE | Audited 80 same-binary GPU trials (8 per fixture), 43 preflight tests and corrected signature analyses. Geometry and accepted-state checks stayed fixed; atomic ordering changed solver color schedules. Identical-code GPU p50 B/A ranges 0.8665–1.1282, so subpercent cross-schedule wins are unqualified. Next: measurement-only deterministic arithmetic replay. |
| 2026-10-19 | G5 deterministic measurement — BOUNDED PASS / TEST ONLY | Reviewed local 180-run headless batch, 150 deterministic accepts/10 expected rejections, 20 native accepts, two safe-envelope failures, and 1,513 verified file hashes. Canonical schedules, iterations and FP64 results repeat; 1,024-body scheduling cost ~46.954 ms, runtime still varies. Default production and solver unchanged; G5 open. |
| 2026-10-19 | G5 post-color barrier coalescing — REJECT / RESTORE | Verified 1,984 archived file hashes, 240 serialized headless runs, all ten matched summary rows, 46 preflight and 49 restored-baseline tests. Control/candidate physics and FP64 signatures matched exactly; 1,024-body nominal solver gain was below 4.36% A/A floor, and aggregate full-tick interval crossed no-effect. Active shader restored byte-for-byte; G5 remains open. |
| 2026-10-19 | G5 contact-local FP64 body snapshots — REJECT / RESTORE | Checked all 1,986 archive hashes, 240 same-schedule GPU trials, 230 accepted + 10 expected rollback-verified rejects, 46 preflight and 49 restored-baseline tests. Solver p50 142.93→138.69 ms at 1,024 bodies; paired ratio 0.97491 CI crosses 1 and 5.32% A/A floor. Aggregate complete-tick test passed, primary failed; retained shader restored. Separate experiment branch pushed, not merged. |
| 2026-10-19 | G5 bounded Anderson convergence — REJECT / RESTORE | Audited 240 recorded Windows trials, 20 residual probes, 2,159 file SHA-256 entries and unit logs. Candidate had 93 accepted vs 115 controls, losing convergence in eight prior-passing fixture/policy configurations. Lower candidate timing on rejected ticks cannot count as speedup. Shader restored exactly; experiment evidence branch remains unmerged. |
| 2026-10-19 | G5 priority gate disposition — DEFERRED / CURRENT WORKSTREAM CLOSED | Ended active G5 optimization after repeated inconclusive micro-gains and algorithmic convergence regression. G5 remains technically not qualified; keep baseline and proofs. Allow independent G6 scoping and other engine development, but do not approve formal G6, large-island claims or release without scope-specific qualifying evidence/risk decision. |
| 2026-10-19 | G6-P1 immutable accepted-state publication — LOCAL PREPARATION PASS | Audited `g6-p1-state-isolation-20261019` source and recorded 21/21 headless PASS processes, zero reported validation errors, 422 verified ZIP hashes, and two 32-sample AB/BA repeats per timing workload. Bounded GPU snapshot/lease API prevents tested retained-consumer aliasing; idle p50 GPU 262→263.75 μs, CPU submit 212.5→213.5 μs, two-slot capacity-32 overhead 128 KiB. Actual device loss/viewer lifecycle and formal G6 remain unverified. |
| 2026-10-19 | G6-P2 bounded GPU resource ownership — LOCAL PREPARATION PASS | Reviewed isolated branch `g6-p2-resource-ownership-20261019`, 22/22 recorded headless process passes, 0 reported validation errors and 252 verified ZIP hashes. Shared-read/exclusive-write claims, queue/fence-retained consumers and cancellation/failure cleanup pass; GPU allocations/committed memory unchanged. Break timing mode shift still unexplained; real app/device-loss qualification open. G5 stays deferred; G6 not qualified. |
| 2026-10-19 | G6-P3 real renderer consumer — LOCAL PREPARATION PASS | Audited 14 PASS Windows headless processes and all 877 archive hashes. Actual offscreen viewer `DrawInstanced` consumes accepted immutable snapshots through P2 leases/fences; 32 physics DXIL pairs unchanged. Render p50 18.432 μs, CPU acceptance wait 1,131.8 μs, offscreen committed memory −192 KiB and three allocations fewer. No `Present`, pixel output or physical device loss tested; G5 deferred, G6 not qualified. |
| 2026-10-19 | G6-P1/P2/P3 + playable branch integration — RECONCILED / NOT G6 QUALIFIED | Integrated cumulative tested development ancestry with main documentation-only history. Kept complete living architecture document and current development README/AGENTS rules, corrected stale 3→5 resource-limit comment. No solver algorithm or compiled binary altered. A separate Windows validation is required after integration; G5 deferred, G6 not qualified. |
| 2026-10-19 | G6-P4 nonblocking accepted-state renderer — LOCAL PREPARATION PASS | Audited 149 archive hashes, 11 PASS final records (6 fresh/5 reused) and 14 timing summary rows against 32 raw samples per arm. Native gated producer test completes two real prior-accepted-generation draws; command acknowledgments still wait on their matching tick. CPU acceptance p50 366.5→0 μs; CPU handoff 751.3→347.0 μs; GPU physics tick 602.5→786.5 μs, render 16.384→22.528 μs; age 0→1 tick. P4 source remains on diverged branch, not integrated into main; G5 deferred, G6 not qualified. |

---

**Source map:** [Main engine code](../physics.c) · [Spatial search](../spatial.c) · [Storage](../storage.zig) · [Entity identity](../entity.zig) · [Viewer](../viewer.c) · [Playable branch](https://github.com/Cryosimorgh/GPU-physics-engine/tree/billiards-playable-requalification-20261018) · [Playable headless workflow](https://github.com/Cryosimorgh/GPU-physics-engine/blob/billiards-playable-requalification-20261018/dev_test.py).
