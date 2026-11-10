# Test branch and production hygiene

## Source-tree pruning: 2026-11-10

The pre-prune `main` state is preserved on `archive/pre-source-prune-20261110`. Draft PR #13 removes tracked artifacts from the proposed production tree: `zig-out/` binaries, distribution bundles, experimental patch handoffs, `evidence/` logs and data, `examples/` captured run outputs, and the G7/P10 handoff ZIP directories. These are not deleted from Git history and must not be silently replaced with fabricated new qualification evidence. Retain exact historical commit links when citing prior measurements.

The remaining root `*.dxil` objects are retained for compatibility with existing native launch and packaging paths until build-from-source parity is established. `third_party/imgui` is a native GUI dependency, not clutter. Python remaining in production is a known migration liability, not an endorsed permanent architecture; builders, shader generation, packaging, G7 scenario code and the `sunder_world.py` API must be replaced or intentionally retired after parity checks. Do not weaken numeric acceptance or remove coverage simply to meet a file-count target.


The `test` branch was created from `main` on 2026-11-05 before the cleanup, so existing diagnostic scripts and tests remain recoverable. Changes to production code go through normal review into `main`; add new stand-alone tests and one-off test harnesses to `test` instead.

## What stays on production branches

- Zig, C, C++, HLSL sources required for native execution and shipping builds.
- Python build, shader generation, packaging and public-world API scripts required by supported entrypoints.
- Existing coupled native verification code, until its build and CI dependencies have been separated without loss of coverage.

## What belongs on `test`

- New `test_*.py`, `test_*.cpp`, `tests.zig`, `*_tests.zig`, and standalone `adversarial.zig`-style harness files.
- Experimental, one-off and obsolete G6/P8 analysis or qualification scripts.
- New high-cost stress and qualification harnesses. Keep measurements and logs out of production source.

The `production-test-file-policy` workflow rejects new standalone tests in pull requests to `main`. Python build provenance utilities have been extracted into `build_support.py`, and production CI stages required tests from `test` without committing those files to production. Existing native verification sources that are linked into production builds, such as `physics_tests.c`, must remain until their host linkage can be separated without changing the existing GPU validation boundary.

To run existing regressions locally, check out `test` and selectively cherry-pick or apply the proposed production source changes to that tree. Do not blindly merge a deletion commit from `main` into `test`: the merge can delete preserved test files. Do not interpret a successful compiler run as a GPU qualification. Maintain the test branch when the stable API or build layout changes.
