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

The `production-test-file-policy` workflow rejects new standalone tests in pull requests to `main`. Python build provenance utilities have been extracted into `build_support.py`, and production CI stages required tests from `test` without committing those files to production. Existing native verification sources that are linked into production builds, such as `physics_tests.c`, must remain until their host linkage can be separated without changing the existing GPU validation boundary.

To run existing regressions locally, check out `test` and selectively cherry-pick or apply the proposed production source changes to that tree. Do not blindly merge a deletion commit from `main` into `test`: the merge can delete preserved test files. Do not interpret a successful compiler run as a GPU qualification. Maintain the test branch when the stable API or build layout changes.
