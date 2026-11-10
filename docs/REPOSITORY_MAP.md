# Sunder source map — 2026-11-10

## What belongs in the active production tree

| Area | Purpose | Status |
|---|---|---|
| `*.zig`, `build.zig` | Native host modules and Zig build entrypoint | Keep; `build.zig` presently builds the storage target only |
| `*.c`, `*.cpp`, `*.h`, `*.inc` | D3D12 runtime, Physics3 host, G7 visual application, native contracts | Keep required code; linked verification sources cannot be deleted by filename alone |
| `*.hlsl` | GPU compute/graphics shader sources | Keep |
| Root `*.dxil` | Previously compiled shaders used by older launch/build paths | Retain provisionally until source-only rebuilds prove parity |
| `third_party/imgui/` | Vendored native UI implementation | Keep |
| `*.json` schemas and generated `*-layout.h` / `layout.zig` | Shader/CPU ABI layout contracts | Keep and verify regeneration before replacing generators |
| `LaunchBenchmark.bat`, `LAUNCH_G7_CAPABILITIES_DEMO.cmd` | Native G7 interactive entrypoints | Keep, but G7 build currently invokes Python |
| `build_*.py`, `generate*.py`, `windows_sdk.py`, `build_support.py` | Native compilation, shader/layout generation, SDK discovery, caching | Transitional Python: replace with Zig build steps after parity tests |
| `sunder_world.py`, `g7_scenarios.py`, `run_g7.py` and related Python | P10 public world API and G7 qualification harness | Transitional Python: API migration needs explicit compatibility and hardware qualification |
| `.github/workflows/` | Continuous checks and native compilation | Keep until equivalent Zig/Workshop test entrypoints run |

## Removed from production tracking (preserved on archive)

- `zig-out/`: 12 generated EXEs; rebuild outputs, not primary source
- `evidence/`: 138 tracked historical qualification files, including nested log collections
- `examples/`: 50 captured run outputs (not example source implementations)
- `G7-RESULTS-TO-SEND/` and `P10-RESULTS-TO-SEND/`: 5 delivery ZIPs
- `dist/`: 4 tracked package bundles, checksums or package metadata files
- `experiments/`: 3 historical G5 patch files

These 212 tracked files were removed only from the proposed production branch. The untouched pre-prune main revision is available at [archive/pre-source-prune-20261110](https://github.com/Cryosimorgh/Sunder/tree/archive/pre-source-prune-20261110). Do not treat old artifacts as tests of a new commit.

## Next migration, in order

1. **Zig build parity:** Extend `build.zig` to build the native G7 app, Physics3 DLL, and HLSL shaders with SDK/DXC discovery, reproducible caches, and no Python. Preserve existing launch semantics.
2. **Zig test/Workshop interface:** Route CPU contract tests, native headless GPU tests, fixed-step correctness, build checks, and benchmark entrypoints through `zig build test`, `zig build bench`, and Workshop as appropriate. Do not assume Workshop files already exist in this checkout.
3. **API migration:** Define replacement for Python's world API and scenario generation with explicit ABI and numerical parity. Keep Python until validated, then retire it in a separate PR.
4. **Compiled-shader cleanup:** Once cold builds work on Windows without tracked DXIL, stop tracking root `*.dxil`. Keep physical-GPU qualification as a separate gate.
5. **Performance investigation:** After source-only launch and stable testing, measure CPU frame time, GPU queue/tick timeline, synchronization waits, render submits, frame-time percentiles, body/contact counts, and memory pressure before changing solver or rendering.

## Guardrails

This is repository hygiene, **not a native GPU regression run or performance fix**. CI compilation cannot establish real D3D12 device performance. Previously accepted and rejected solver conditions remain unchanged. If documentation or old measurement links refer to pruned paths, use the archive revision or their original immutable commit.
