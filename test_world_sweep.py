"""Qualification verdict tests; mocked processes do not qualify GPU physics."""
from contextlib import ExitStack, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_world_sweep as sweep


class SweepVerdictTests(unittest.TestCase):
    def run_sweep(self, failed_case):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            run = root / "runs" / "verdict-test"
            replacements = {
                "ROOT": root, "BASE": root, "RUN": run,
                "RUN_ID": "verdict-test", "digest": lambda: {},
                "SOURCES": (),  # Source presence is tested separately from verdict ordering.
                "git_revision": lambda: "test-commit",
                "tracked_changes": lambda: [], "driver_inventory": lambda: [],
            }
            for name, value in replacements.items():
                stack.enter_context(patch.object(sweep, name, value))
            stack.enter_context(patch.object(sweep.platform, "system", lambda: "Windows"))
            stack.enter_context(patch.object(sweep.sys, "argv", ["run_world_sweep.py", "--full"]))

            def execute(name, args, result, *rest):
                ok = name != failed_case
                result["tests"].append({"name": name, "status": "PASS" if ok else "FAIL"})
                return ok

            stack.enter_context(patch.object(sweep, "execute", execute))
            with redirect_stdout(StringIO()):
                code = sweep.main()
            return code, json.loads((run / "consolidated.json").read_text())

    def test_each_failed_gate_is_no_go_including_final_stress(self):
        for failed_case in sweep.CASES:
            with self.subTest(failed_case=failed_case):
                code, result = self.run_sweep(failed_case)
                self.assertNotEqual(code, 0)
                self.assertFalse(result["qualified"])
                self.assertEqual(result["status"], "NO-GO")
                self.assertEqual(result["failure"], "first failing gate: " + failed_case)
                self.assertEqual(result["tests"][-1]["name"], failed_case)
                index = sweep.CASES.index(failed_case)
                self.assertEqual(result["unexecuted"], list(sweep.CASES[index + 1:]))

    def test_all_gates_pass_can_qualify(self):
        code, result = self.run_sweep(None)
        self.assertEqual(code, 0)
        self.assertTrue(result["qualified"])
        self.assertFalse(result["unexecuted"])


if __name__ == "__main__":
    unittest.main()
