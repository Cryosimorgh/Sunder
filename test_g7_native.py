"""Focused native entry points. Requires Windows and a physical D3D12 adapter."""
from pathlib import Path
import json
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent
EXE = ROOT / 'zig-out/bin/SunderG7.exe'
EVIDENCE = ROOT / 'evidence/g7/native-showcase'

@unittest.skipUnless(os.name == 'nt', 'NOT RUN: physical Windows D3D12 adapter required')
class NativeShowcase(unittest.TestCase):
    def run_case(self, name, *args):
        p = subprocess.run([str(EXE), *map(str, args)], cwd=ROOT, capture_output=True, text=True, timeout=180)
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
