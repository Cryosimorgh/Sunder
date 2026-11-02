# Experimental G7 scalable native benchmark (PR #11)

This is an unmerged experimental implementation, not a new qualification approval. The existing G7 512/1K numerical acceptance record remains unchanged. Large native populations are **NOT QUALIFIED**.

## Directly editable controls

The G7 ImGui panel accepts exact 64-bit unsigned population counts, rather than a slider capped at 1K. It also exposes spawn batch and rate, radius/mass and variation, restitution, friction, gravity X/Y/Z (independent cube/belt Z default), initial rain velocity, spatial cell, native contact budget, solver iterations, placement attempts, emitter width/height, belt geometry/speed/spin and cube velocity. Camera FOV, clipping, window size and playback speed are independently editable. Numeric input is validated rather than silently clipped to preset slider bounds.

Body count/contact budget/solver iteration edits rebuild the native physics context and renderer. The replacement is admitted and seeded before retiring the old context. If preadmission fails, the old accepted scene continues. On success, resizing currently starts a fresh scene epoch; it does not yet migrate the moving bodies. Other scene settings apply on Reset. No physics validation predicates are relaxed.

The old 100K G7 allocation and 1M native body / 16M contact admission presets are removed. GPU capability is **not unlimited**: the native shaders use 32-bit byte-addressed SoA buffers, and D3D12 runtime buffers support up to 4 GiB. At 192 bytes per sphere plus 256 bytes of resource guard, the representable maximum is floor((2^32 - 256)/192) slots; the 128-byte contact records have an analogous floor((2^32 - 256)/128) bound. Available GPU budget, memory allocations, and correctness may impose much lower effective limits. The former 4096-iteration admission ceiling has also been removed; iterations are still stored as native unsigned 32-bit values. Very large requests are unqualified and can trigger GPU timeouts or unacceptable performance.

## Example commands

Build first using LAUNCH_G7_CAPABILITIES_DEMO.cmd or the usual Python build. The retained regression baseline is 1K population for 600 frames. Override it explicitly:

~~~powershell
.\zig-out\bin\SunderG7.exe --render-bench --count 250000 --batch 128 --contacts 4000000 --iterations 1024 --frames 600
.\zig-out\bin\SunderG7.exe --render-bench --count 10000 --radius 0.25 --mass 2 --gravity-z -9.81 --spawn-hz 2 --frames 300
~~~

Supported render-benchmark flags include --count, --batch, --contacts, --iterations, --radius, --mass, --radius-spread, --mass-spread, --restitution, --friction, --gravity-x, --gravity-y, --gravity-z, --gravity-other-z, --cell, --spawn-hz, --seed, --scene, --placement-attempts, --initial-vz, --cube-speed, --belt-closing-speed, --belt-spin, --belt-major-radius, --belt-minor-radius, --emitter-width-x, --emitter-width-y and --emitter-height.

A separate native capacity ramp tests progressively larger freshly constructed full-population physics worlds:

~~~powershell
.\zig-out\bin\SunderG7.exe --fill-until-limit --start 512 --batch 32 --ticks 8 --multiplier 2
.\zig-out\bin\SunderG7.exe --fill-until-limit --start 10000 --max-count 500000 --batch 128 --ticks 32
~~~

The ramp reports last successful body count, first failure, attempts, last admitted population, tracked GPU memory and stopping reason, while preserving per-tick JSONL data. Each ramp step is a fresh scene, not an accumulation of the preceding body's trajectories. A ramp result is an observed workload boundary, not proof of the device's exact maximum.

## Verification status

- CPU scene test: supports more than 100,000 bodies, deterministic torus generation and invalid numeric inputs. Compile using: g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic test_g7_scene.cpp -o test_g7_scene
- Windows CI compiles native G7 host, renderer and physics shaders, but does not run physics on a qualified physical D3D12 adapter.
- Native GPU correctness, large populations, edited parameters, long-term memory behavior, and final regression campaigns must be qualified separately before this feature can merge.
