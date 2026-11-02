"""G7 packaging/visual geometry contracts. Never qualifies native D3D12."""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import run_g7_windows as runner


class G7PackagingTests(unittest.TestCase):
    def test_windows_nested_paths_manifest_integrity_and_unique_handoffs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "launcher" / "run-1"
            (run / "g7-native" / "belts-1000-r0").mkdir(parents=True)
            (run / "p10-native" / "logs").mkdir(parents=True)
            (run / "g7-native" / "belts-1000-r0" / "case.json").write_text(
                '{"status":"NO-GO"}', encoding="utf-8")
            (run / "p10-native" / "logs" / "native.log").write_text(
                "original failure", encoding="utf-8")
            send = root / "handoffs"
            with patch.object(runner, "SEND", send), patch.object(
                    runner, "git", return_value="test-revision"):
                first = runner.bundle(run, "full", {"status": "NO-GO"})
                second = runner.bundle(run, "full", {"status": "NO-GO"})
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_file())
            self.assertTrue(second.is_file())
            self.assertEqual(len(list(send.glob("*.zip"))), 2)
            with zipfile.ZipFile(first) as z:
                paths = set(z.namelist())
                key = "g7-native/belts-1000-r0/case.json"
                self.assertIn(key, paths)
                self.assertIn("p10-native/logs/native.log", paths)
                self.assertFalse(any("\\\\" in name for name in paths))
                import json
                manifest = json.loads(z.read("MANIFEST.json"))
                self.assertEqual(
                    hashlib.sha256(z.read(key)).hexdigest(),
                    manifest["sha256"][key])
                self.assertEqual(manifest["result"]["status"], "NO-GO")
                self.assertEqual(z.read("p10-native/logs/native.log"), b"original failure")


class VisualMathTests(unittest.TestCase):
    def test_orbit_projection_has_depth_and_zoom(self):
        try:
            from g7_visual_demo import camera_project
        except (ImportError, ModuleNotFoundError) as exc:
            self.skipTest("tkinter not installed in this CPU-only environment: " + str(exc))
        center = camera_project((0., 0., 0.), 800, 600, 12, 0., .4)
        self.assertAlmostEqual(center[0], 400.)
        self.assertAlmostEqual(center[1], 300.)
        near = camera_project((1., 0., 0.), 800, 600, 12, 0., .4)
        far = camera_project((-1., 0., 0.), 800, 600, 12, 0., .4)
        self.assertGreater(near[2], far[2])
        zoom = camera_project((0., 1., 0.), 800, 600, 12, 0., .4, 2.)
        normal = camera_project((0., 1., 0.), 800, 600, 12, 0., .4, 1.)
        self.assertGreater(abs(zoom[0] - 400), abs(normal[0] - 400))


if __name__ == "__main__":
    unittest.main()
