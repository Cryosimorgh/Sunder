# Sunder P10 — Run on your actual Windows GPU

This suite is for **PR #8**, branch `p10-headless-world-api-20261031`.
It performs the hardware-dependent qualification that the Windows cloud
runner could not perform. It runs **without a GUI, mock physics, or shader
modifications**.

## Prerequisites

Use a Windows 10/11 x64 machine with a functioning hardware **D3D12 compute GPU**
with shader double-precision support and enough available GPU memory for the
requested 1M separated-pair stress case. The suite records real admission
failures rather than skipping the case.

Install these on the host, then start a fresh Command Prompt:

- Python 3.12 x64, available as `python` in PATH.
- NumPy: `python -m pip install numpy`
- Zig **0.15.2** executable in PATH: `zig version`
- Windows 10/11 SDK with D3D12 headers, UCRT and DXC: `windows_sdk.py`
  locates it automatically. No Visual Studio IDE is required if those components
  are already installed.
- Git for repository checkout and commit provenance.

## One-time checkout

~~~powershell
git clone https://github.com/Cryosimorgh/Sunder.git
cd Sunder
git switch p10-headless-world-api-20261031
~~~

If the repository already exists locally, fetch the branch without resetting
or overwriting your work:

~~~powershell
git fetch origin p10-headless-world-api-20261031
git switch p10-headless-world-api-20261031
~~~

For reliable provenance, keep the checkout clean and run against the committed
branch. Do not run a modified local shader or a stale binary. The build script
verifies and compiles all nine shaders and the isolated physics DLL.

## One-click test

**Double-click `RUN_P10_WINDOWS.cmd` in the repository root.**

Or in Command Prompt:

~~~cmd
RUN_P10_WINDOWS.cmd
~~~

The launcher runs `python run_world_sweep.py --full` **exactly**, with all tests
mandatory, and **always** executes the evidence packager afterward, even after
a failed/partial run. The runner stops at the earliest failing gate and marks
every remaining case NOT RUN. The original failure is preserved in a unique
run directory; reruns never overwrite it.

The full required gate sequence is:

1. CPU host lifecycle tests (explicitly *not* GPU qualification).
2. Windows Zig/DXC build of the unchanged D3D12 physics DLL and nine shaders.
3. Empty authored GPU world and two independent numerical replays.
4. **Native application-world adversarial suite**: generation reuse, CRUD,
   static policy, capacity growth, gravity/force/impulse, collision energy
   transfer/friction, sleep/wake, three simultaneously held native snapshots,
   backpressure, an injected rejected GPU tick with immutable rollback,
   stale handles, cross-world isolation and two independent numerical replays.
5. Sixteen-body authored GPU world + independent replay.
6. 1,024-body authored GPU world + independent replay.
7. Existing native CPU-oracle checks (KKT, collision completeness, momentum,
   energy, sleep, plane contact, numerical rollback and native consumers).
8. Existing full planar pool/rail and device/ownership regressions.
9. Original 10K / 100K / 1M genuine GPU collision-bearing **separated-pair**
   stress. These are not arbitrary large connected physics scenes.

All mandatory gates must run and pass for a scripted GO. No GPU result is
invented if hardware lacks memory or D3D12 capabilities. Historical P9
bitwise replay is explicitly not a new P10 requirement.

## What to send back

When the window finishes, open:

`P10-RESULTS-TO-SEND`

**Upload the newest `Sunder-P10-<run-id>-GO/NO-GO-<UTC>.zip` here.** Upload it
even if the test says NO-GO. There is no need to manually copy console text,
screenshots, binaries, or temporary directories.

The ZIP contains the exact per-run consolidated JSON, commands, raw case logs,
per-tick GPU/host p50/p95/p99/worst, accepted/rejected ticks, deadlines,
tracked memory, source hashes, D3D12 adapter/driver information, build manifest,
independent replay comparison, topology declarations, and a SHA-256 file
inventory. The independent native CPU-oracle logs remain separate from the
production-path timings. Prior runs are retained at
`evidence/p10/world-sweep/runs/<run-id>/`; any source failure remains in the
original directory, not rewritten as a pass.

**GO means the scripted gates passed**, not automatic authorization to merge.
I will inspect the archive, verify hashes and physics evidence, identify defects
if any, and decide whether PR #8 should move beyond draft.

If the machine crashes or the script is interrupted before packaging, keep
the `evidence/p10/world-sweep` directory unchanged and run
`python package_p10_evidence.py` in the repository root to package the latest
completed run. Repeating the sweep creates another run rather than overwriting
the old evidence.
