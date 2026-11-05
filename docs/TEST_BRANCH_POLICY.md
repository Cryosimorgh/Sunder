# Test branch and production hygiene

The `test` branch was created from `main` on 2026-11-05 before the cleanup, so existing diagnostic scripts and tests remain recoverable. Changes to production code go through normal review into `main`; add new stand-alone tests and one-off test harnesses to `test` instead.

## What stays on production branches

- Zig, C, C++, HLSL sources required for native execution and shipping builds.
- Python build, shader generation, packaging and public-world API scripts required by supported entrypoints.
- Existing coupled native verification code, until its build and CI dependencies have been separated without loss of coverage.

## What belongs on `test`

- New `test_*.py`, `test_*.cpp`, `tests.zig`, `*_tests.zig`, and standalone `adversarial.zig`-style harness files.
- Experimental, one-off and obsolete G6/P8 analysis or qualification scripts.
- New high-cost stress and qualification harnesses. Keep measurements and logs out of production source.

The `production-test-file-policy` workflow rejects newly introduced stand-alone test files in pull requests to `main`. The policy intentionally does not delete existing interdependent test files: `dev_test.py` supplies build helpers for currently supported binaries, and native files such as `physics_tests.c` are linked by current build scripts. Move those only after splitting shared build utilities and updating CI plus Windows hardware qualification.

To run existing regressions, check out `test` and merge or cherry-pick the proposed production change into that working tree first. Do not interpret a successful compiler run as a GPU qualification. Maintain the test branch when the stable API or build layout changes.
