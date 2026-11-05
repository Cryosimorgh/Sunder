# Sunder test branch

This is the dedicated home for standalone Python, Zig and C++ tests, native qualification harnesses, and historical G5/G6 diagnostic scripts. Those sources are intentionally excluded from the proposed production tree.

The production files changed by draft PR #13 were overlaid here at commit `ce4dfe19ee055d32eea07164c42fdac17a9984ab` without copying production deletions, so existing test files remain intact. The test-branch source must be synchronized to the exact production revision before reporting qualification. Do not blindly merge production cleanup/deletion commits into this branch; selectively cherry-pick source changes or refresh relevant source files while retaining test-only files.

Run:
```powershell
python -m unittest test_g7_scenarios test_g7_infrastructure test_sunder_world test_p10_packaging test_world_sweep -v
zig test tests.zig -O ReleaseSafe
zig test test_reference_state.zig -O ReleaseSafe
```

On Windows with a suitable D3D12 adapter, run the appropriate bounded native gates via `python dev_test.py`, `python run_world_sweep.py --full`, or the documented launchers. Native GPU physics qualification cannot be inferred from CI CPU tests or compilation. Historical scripts are preserved for reproducibility, not endorsed as current production workflows.
