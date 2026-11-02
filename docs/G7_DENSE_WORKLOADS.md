# G7 — Dense Dynamic Collision Workloads (experimental implementation)

**Branch:** `g7-dense-dynamic-collision-workloads-20261102` (based on P10 merged `main` 8a5385b).  
**Qualification:** **NO-GO / NOT RUN** until full native Windows x64/D3D12 hardware
correctness and raw evidence review. A GitHub CI CPU PASS or compilation alone
does **not** qualify the GPU. No P10 physical tolerance, iteration bound, or
legacy P9/G5 requirement has been relaxed.

## Workloads

`cube`: a cubic **spawning volume**, not a rigid-body cube collider. All
entities are P10 spheres. The seeded shuffled 3D lattice is filled in successive
per-tick batches to the requested slot limit. It uses radius/mass variation
and guaranteed initial spacing. Bodies are **active static spheres** during filling so even nonzero authored
gravity cannot displace them into late-insertion overlaps. They become dynamic
with their authored masses and chosen velocity field on the **tick after**
the final fill is accepted. These active static spheres are not unused slots. Isolated, moderate and dense velocity/pitch presets are
available. Every attempt, provisional handle, accepted count, post-fill tick,
rejection, cause and boundary error is recorded.

`belts`: two 3D toroidal clouds of independently authored spheres (major
and minor radii and centers are recorded). A seeded 3D clearance hash rejects
initial intersections. Belts initially have separate centers and positive
x-gap, close along opposite x directions and spin around the x axis in
opposite directions by default. This uses **no self-gravity**, CPU contact
solver, hard-coded pairs or flat 2D geometry. Their trajectories may still
reject under P10's existing physical envelope or solver limits; such runs
are NO-GO rather than a substituted weaker workload.

The authored domain remains `[-512,512]` for every coordinate. Both scenes
obey P10's radius and fixed-step policy. Scale presets use 1K, 10K and 100K
bodies; >100K (including 1M) requires `--allow-large`, an adequate
`--max-committed-mib` admission budget, and native hardware success. No
unexecuted scale is claimed.

## Native 3D capabilities application (2026-11-02)

Double-click `LAUNCH_G7_CAPABILITIES_DEMO.cmd` on Windows x64.
`LAUNCH_G7_DEMO.cmd` is a compatibility alias for the same native application.
Prerequisites: Python 3.12, Zig 0.15.2 on PATH, and the Windows SDK with DXC,
D3D12 headers and libraries. NumPy is needed for the Python tests, not the
native executable. The launcher builds missing or changed dependencies using
source/tool/output hashes. It then starts `zig-out/bin/SunderG7.exe`.
Build logs are in `evidence/g7/native-showcase/`.

Direct execution from `zig-out/bin` or another working directory is supported.
The executable resolves the project root from its own location, then loads the
physics/render shaders and writes evidence there. Missing shaders report the
asset path and the build launcher instead of a generic device/admission failure.

`g7_demo.cpp`, `g7_scene.h`, and `g7_render.hlsl` implement a dedicated
Win32/D3D12 application. Perspective sphere impostors perform analytic ray/sphere
intersection, write the sphere surface depth, and use lighting and highlights.
One instanced draw renders the admitted population. The existing pinned ImGui
Win32/DX12 backends supply the controls. The application starts playing.

### Controls

- Left drag: orbit; right or middle drag: pan; wheel: zoom; Home: camera reset.
- Space: play/pause; R: reset; F11: borderless fullscreen; H: cinematic HUD toggle.
- Scene selection switches between the living cube and separated blue/orange
  toroidal belts. Both fill in deterministic batches before activation.
- 100, 500 and 1K presets, body count, batch, spawn frequency, seed, density,
  radius/mass variation and gravity are available. Settings apply on Reset.
- Playback changes fixed-step scheduling; physics dt stays exactly 1/128 s.
  Step requests one native tick. Follow cloud uses the accepted GPU centroid
  for rendering only. High quality changes the specular shading.
- Native diagnostics distinguish FPS, native GPU tick, tick wall time and
  OS thread CPU time. Thread CPU measurements have OS timer resolution.
  They show admitted/requested bodies, rejected admissions, accepted/rejected
  ticks, constraints, candidates, degree, allocation memory, adapter/driver,
  seed/revision, decoded rejection bits and accepted-snapshot display status.
- Sample contact topology explicitly reads the last successful contact buffer.
  Geometric contacts use raw gap <= 0; the largest island and cross-belt edges
  use those actual geometric edges only. Sampling adds overhead. Trails and
  contact flash effects are not implemented.

### Accepted-state ownership

The physics worker and renderer serialize all Physics3 calls with an SRW lock.
The render thread tries the lock without waiting for a physics tick. On success,
it acquires an accepted `Ph3Lease`, validates the native resource through the
small internal bridge in `g7_native.h`, and records a GPU-to-GPU copy into its
own immutable display buffer. It tracks the graphics completion fence before
submission and releases the lease after submission. The producer's read claim
survives until the fence completes. COMMON buffer promotion/decay on the DIRECT
consumer queue avoids changing the producer's recorded resource state. The
renderer waits for its previous frame before reusing its snapshot/allocator.
If physics is busy it renders the previous completed GPU snapshot. There is
no per-frame CPU body readback or interpolated collision outcome. Reset waits
for outstanding leases; rejected ticks retain the previous admissions and GPU
state. The native delayed-reader and rejection rollback checks exercise this.
Signal/wait failures quarantine unfenced work rather than free in-flight data.

The native solver has 1,000 fixed slots, including static parked unused slots.
Only admitted slots are drawn and counted as active bodies. The UI separately
reports native published slots. Logical identities are `(scene epoch, slot, 1)`;
a scene reset starts a new epoch. Native accepted ticks keep their global clock.
This avoids capacity migrations and full-state CPU snapshots in the display path.

### Failure diagnosis and separate default envelope

The historical seed-7 dense radial cube remains an **unsupported stress case**.
The original 512-body / batch-64 viewer accepts fill tick 8, then rejects the
first dynamic tick with flags 12, 6,220 constraints and maximum degree 32.
New diagnostic witnesses identify normal/tangent KKT failure and penetration:
normal residual/tolerance up to 14,059x, tangent up to 31,057x and penetration
0.003741 units in the diagnostic reproduction. Counts are partial because
validation remains fail-closed. Initial spacing is non-overlapping, admission
and contact capacity are adequate, and activation applies the intended field.
Slower radial compression still rejects later. More iterations alone are not
claimed to qualify that original workload.

The separately identified native default uses aligned opposing x waves in a
3D cube, radius +/-3%, mass +/-10%, speed 0.7, pitch 2.3 radii; the belts use
closing speed 0.6 and opposite angular rates 0.025. Cell size is 1.0, contact
capacity 12,000, and the **application** solver budget is 512 iterations. The
headless engine defaults, solver equations, acceptance expressions and all
physics tolerances are unchanged. At 128 iterations late KKT failures occurred
in the 1K cube and both belts. These rejected experiments are retained.
This is a bounded demo envelope, not qualification of arbitrary dense radial
collapse, edited parameters, arbitrary seeds, or 10K/100K/1M populations.

### Local native measurements and remaining gate

Physical adapter: NVIDIA GeForce RTX 4070 Ti SUPER; driver 32.0.16.1088.
Four 512-iteration cases (512/1K cube/belts, seed 7) each accepted 768 native
ticks with zero rejections in the initial bounded run. Cross-belt geometric
contacts were 16 (512) and 12 (1K), with positive native impulses in both.
Native physics memory was 4,653,056 bytes, separately from rendering allocations.
The final repeated run and raw per-tick logs accompany the focused handoff.

A 1K / 1920x1080 render run measured 600 frames in 10.210 seconds, 58.77 render
FPS and mean 60.8 microseconds GPU render time including the GPU snapshot copy.
Native physics averaged roughly 49-56 milliseconds per tick in sampled headless
runs. Contact readbacks are diagnostics outside native GPU tick timestamps.
The application slows simulated time when the hardware cannot sustain 128 ticks/s;
it never enlarges dt or drops rejected ticks. Rendering FPS is not physics TPS
or an OS-confirmed displayed-frame/latency measurement. This is local evidence
with other user applications running, not an exclusive-adapter benchmark.

28 CPU contracts, eight P10 native oracle groups, eight native-world acceptance
groups, and three native G7 lifetime/lifecycle/controlled-removal tests passed.
Lifecycle coverage includes scene resets/switches, resize, fullscreen, camera
changes, pause/step, minimize/restore, repeated executable launches, stale lease
rejection, delayed GPU readers, and byte-for-byte rejected-tick rollback.
Controlled `ID3D12Device5::RemoveDevice` is an API fault test; physical adapter
removal, long leak campaigns and independent final-head acceptance are **NOT RUN**.
The visual reference URL could not be fetched (online throttling); no reference
video match is claimed. PR #9 remains **draft / NO-GO for merge** pending review
of this bounded native evidence and final user visual acceptance. G5/G6 and
release qualification do not change.

Reproduce the targeted checks:

```shell
python build_g7_demo.py
python reproduce_g7_failure.py
python -m unittest test_g7_scenarios test_g7_infrastructure test_sunder_world test_world_sweep test_g7_native -v
python test_physics3.py --smoke
python test_native_world.py
zig-out/bin/SunderG7.exe --verify 512 0 768
zig-out/bin/SunderG7.exe --verify 512 1 768
zig-out/bin/SunderG7.exe --verify 1000 0 768
zig-out/bin/SunderG7.exe --verify 1000 1 768
zig-out/bin/SunderG7.exe --render-bench --frames 600
```

Scene 0 is cube; scene 1 is belts. Verification reads contact records explicitly
for native impact evidence. It is not the production render timing path.
The old `g7_visual_demo.py` remains a Tkinter diagnostic only; launch it manually
with Python if needed. It is no longer the primary capabilities demo.

## Reproduce

On Linux (scene and host contracts **only**):

```shell
python -m pip install numpy
python -m unittest test_g7_scenarios test_sunder_world -v
```

On Windows with a working **hardware D3D12 compute adapter**:

```bat
RUN_G7_WINDOWS.cmd --quick
RUN_G7_WINDOWS.cmd --full
```

Full is the default mode; it calls `build_physics3.py`, the G7 and existing
P10 host tests, `run_g7.py --scenario both --full`, and the existing
`run_world_sweep.py --full` native correctness gate. At least two fresh
native instances are used per G7 case. If a prior run failed *only* while verifying the handoff ZIP, do
**not** repeat the costly native benchmark. Preserve the entire original
`evidence/g7/launcher/<run-id>/` directory and run:

```powershell
python run_g7_windows.py --package-existing latest
```

This selects the newest existing launcher run, preserves original
case-level GPU/P10 failure logs, writes a **new uniquely named**
`G7-RESULTS-TO-SEND/*.zip`, and verifies each member against a
SHA-256 manifest with platform-independent POSIX archive paths. You may
instead supply an explicit prior launcher directory after
`--package-existing`. This is an archive-only recovery, **not** a
test rerun or changed qualification verdict.

The launcher always tries to create
**one new unique** `G7-RESULTS-TO-SEND/Sunder-G7-*.zip`, including failure
logs. If Python itself is missing, the CMD creates a minimal failure ZIP
via PowerShell. Do not overwrite or discard original failures.

For a bounded native run:

```shell
python build_physics3.py
python run_g7.py --scenario both --preset dense --bodies 1000 \
  --duration-ticks 96 --spawn-batch 4096 --post-full-ticks 64 \
  --sample-every 8 --repeats 2 --max-committed-mib 2048
```

User options: `--scenario cube|belts|both`, `--preset
isolated|moderate|dense`, `--seed`, `--bodies`, `--duration-ticks`,
`--post-full-ticks`, `--spawn-batch`, `--radius`, `--mass`,
`--cube-size`, `--gravity X Y Z`, `--closing-speed`, `--spin-speed`,
`--counter-rotate/--no-counter-rotate`, `--radius-spread`,
`--mass-spread`, `--velocity-field inward|swirl|funnel`,
`--perturbation`, `--dt`, `--cell-size`,
`--contact-budget`, `--iterations`, `--deadline-ms`,
`--max-committed-mib`, `--sample-every`, `--repeats`, `--quick`,
`--full`, `--allow-large`, and `--output`.

## Evidence semantics

`run_g7.py` emits per-run `ticks.csv`, `ticks.jsonl`,
`samples.jsonl`, `phases.csv`, `phases.json`, `case.json`
and run `consolidated.json`. Contact phase boundaries are **sample-based**
(first observed cross-belt contact, sampled peak and post-peak). Its
bounded GPU readback uses the existing native `ph3_contacts` ABI:
each 128-byte record contains two body indices, signed geometric gap,
and the normal impulse. Record samples distinguish speculative constraints
from actual overlap (`gap<=0`) and positive impulses. Contact topology
counts active components, largest connected island, degree percentiles,
cross-belt edges, and sampled edge churn. Churn between separated samples
is **not** consecutive-tick churn. If native contact readback fails, the
case fails; no graph statistic is fabricated.

Production per-tick timings are separate from diagnostic sampling and final
accepted-state snapshot/CPU comparison. The P10 native GPU timestamps
(`gpu_us`) and host step, native submission/completion, staged upload and
CPU edit timing are recorded independently; phase timings may overlap
accounting categories and must not be summed. Latency percentiles are
computed from accepted ticks only, retaining all rejected-tick evidence.
Native `candidates`, `contacts`, max degree, error bits, memory, deadline
misses, adapter, source hashes and scene initial-state hashes are recorded.
Allocation **event counts** are not exposed by P10; do not report one.

Two independently created native worlds must produce the same seeded
initial-state hash, accepted physics and numerically comparable final
position/velocity states. P9 bitwise replay is **UNSUPPORTED**. The final
readback is a marked diagnostic, not part of production hot-loop timings.

A `PASS` case requires exact body count, accepted steps, physical (not
software/Hyper-V) adapter, and a nontrivial observed collision graph for
dense scenes (cross-belt contacts for belts). A full handoff that passes
automated scripts is marked **PENDING_ADVERSARIAL_REVIEW**, not final GO.
If hardware or a required test is missing, the result is NO-GO/NOT RUN.
Native correctness must be independently reviewed before merging.

## Known limitations and required follow-up

1. Local 512/1K native demo measurements are recorded above. Full headless
   1K/10K/100K qualification and final acceptance remain unmeasured.
2. G7 samples are explicit GPU contact-buffer diagnostics. They can add
   GPU readback overhead between ticks; diagnostic GPU readback and CPU graph
processing are reported separately. Do not conflate sampled cadence
   throughput with an unsampled sustained production run.
3. Belt contacts are examined from the GPU's **pre-integration** contact
   buffer; peak graph/impact phases are diagnosed at sampling cadence, not
   a guarantee of observing the absolute unsampled peak.
4. The proposed 1M arbitrary-connected run is **NOT RUN** and potentially
   exceeds GPU memory/contact budgets. Conservative admission estimates are
   not measured allocations.
5. The accepted P10 sphere model has no N-body gravitational attraction;
   no shape change or general optimizer is added. The native renderer above
   is separate from this headless benchmark.

Follow with the uploaded **Prompt 2 — Adversarial native Windows qualification
and final PR gate** on exactly the tested PR head. Keep the PR draft if any
required case fails or remains unexecuted.
