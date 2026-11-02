"""Focused native entry points. Requires Windows and a physical D3D12 adapter."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
EXE = ROOT / 'zig-out/bin/SunderG7.exe'
EVIDENCE = ROOT / 'evidence/g7/native-showcase'

@unittest.skipUnless(os.name == 'nt', 'NOT RUN: physical Windows D3D12 adapter required')
class NativeShowcase(unittest.TestCase):
    def run_case(self, name, *args, cwd=ROOT):
        p = subprocess.run([str(EXE), *map(str, args)], cwd=cwd, capture_output=True, text=True, timeout=180)
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / (name + '.stdout')).write_text(p.stdout)
        (EVIDENCE / (name + '.stderr')).write_text(p.stderr)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout.strip().splitlines()[-1])

    def test_lease_and_rejection_rollback(self):
        r = self.run_case('lifetime', '--self-test')
        self.assertTrue(r['rollback'])
        self.assertTrue(r['stale_lease_rejected'])
        self.assertTrue(r['delayed_reader'])
        self.assertTrue(r['append_preserves_dynamic'])

    def test_render_benchmark_from_executable_directory(self):
        r = self.run_case('render-from-bin', '--render-bench', '--frames', 600, cwd=EXE.parent)
        self.assertEqual(r['render_frames'], 600)
        self.assertEqual((r['width'], r['height']), (1920, 1080))
        self.assertGreater(r['gpu_snapshot_copies'], 0)
        self.assertEqual(r['physics_rejected'], 0)
        self.assertEqual((r['min_population'], r['max_population']), (1000, 1000))
        self.assertGreater(r['physics_accepted'], r['warmup_accepted'])

    def test_launch_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory(prefix='sunder-g7-cwd-') as directory:
            r = self.run_case('render-from-unrelated-directory', '--frames', 30, cwd=directory)
            self.assertEqual(r['render_frames'], 30)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_playback_scales_native_ticks(self):
        r = self.run_case('playback', '--pacing-test')
        self.assertGreater(r['one_tps'], r['quarter_tps'] * 2.8)
        self.assertGreater(r['two_tps'], r['half_tps'] * 2)

    def test_controlled_device_loss(self):
        r = self.run_case("device-loss", "--device-loss-test", "--frames", 150)
        self.assertTrue(r["controlled_device_loss_handled"])

    def test_real_window_lifecycle(self):
        r = self.run_case('lifecycle', '--ui-test', '--frames', 360)
        self.assertEqual(r['render_frames'], 360)
        self.assertGreater(r['last_gpu_render_us'], 0)
        self.assertGreaterEqual(r['scene_epochs'], 3)

if __name__ == '__main__':
    unittest.main()
