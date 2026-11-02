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

## Visual capabilities demo (new)

Double-click `LAUNCH_G7_DEMO.cmd` on Windows. It builds the native
`physics3.dll` if absent and opens `g7_visual_demo.py` (standard Python
`tkinter` + NumPy). Select **cube** or **belts**, density, a seeded
body count (1–3000), and cube spawn batch. Press Play or Pause,
drag to orbit the 3D camera, and use the scroll wheel to zoom.
Cube mode shows an outlined cubic **spawn volume** containing active
spheres; belt mode draws separate blue/orange toroidal clouds with
opposing native velocities. The right panel reports active/capacity,
GPU contacts and candidates, max contact degree, GPU/host tick times,
staging time, and committed memory.

The visualization is **not** a GPU renderer and **not** a benchmark.
It uses CPU Tk Canvas to draw snapshots explicitly read back from the
native D3D12 sphere solver. The readback overhead is displayed and
must not be included in production GPU benchmark timings. The viewer
never substitutes a CPU physics simulation. A native GPU rejection
stops playback and displays the native error instead of claiming
success. Higher populations belong in the headless benchmark, not
in interactive Canvas rendering.

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

1. Native D3D12 qualification and complete 1K/10K/100K performance tables
   have **not** been measured in this authoring environment.
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
   no renderer, shape change or general optimizer is added.

Follow with the uploaded **Prompt 2 — Adversarial native Windows qualification
and final PR gate** on exactly the tested PR head. Keep the PR draft if any
required case fails or remains unexecuted.
