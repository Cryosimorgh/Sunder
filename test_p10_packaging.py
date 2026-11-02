"""CPU-only integrity checks for the Windows handoff ZIP. Does not qualify GPU."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import package_p10_evidence as p


class PackagingTests(unittest.TestCase):
    def setUp(self):
        temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(temp)
        self.base = self.root/"evidence"/"p10"/"world-sweep"
        self.build = self.root/"evidence"/"p10"/"build"
        self.base.mkdir(parents=True)
        self.build.mkdir(parents=True)
        self.enterContext(patch.object(p, "ROOT", self.root))
        self.enterContext(patch.object(p, "BASE", self.base))
        self.enterContext(patch.object(p, "BUILD", self.build))

    def add_run(self, run_id, qualified):
        run = self.base/"runs"/run_id
        run.mkdir(parents=True)
        (run/"consolidated.json").write_text(json.dumps(
            {"revision":"deadbeef", "qualified":qualified,
             "status":"GO" if qualified else "NO-GO"}))
        (run/"first-failure.log").write_text("REJECTED: original error preserved")
        (self.build/"manifest.json").write_text('{"compiler":"test"}')
        return run

    def test_manifest_integrity_and_nonoverwriting_archives(self):
        self.add_run("20261031T120000Z-aaa", False)
        with patch("sys.argv", ["package_p10_evidence.py"]):
            self.assertEqual(p.main(), 0)
            self.assertEqual(p.main(), 0)
        files = sorted((self.root/"P10-RESULTS-TO-SEND").glob("*.zip"))
        self.assertEqual(len(files), 2)
        for archive_path in files:
            with zipfile.ZipFile(archive_path) as z:
                manifest = json.loads(z.read("CHECKSUMS.json"))
                self.assertFalse(manifest["qualified"])
                self.assertEqual(manifest["source_revision"], "deadbeef")
                for path, meta in manifest["files"].items():
                    self.assertEqual(p.sha(z.read(path)), meta["sha256"])
                    self.assertEqual(len(z.read(path)), meta["bytes"])
                self.assertIn(b"original error", z.read(
                    "evidence/p10/world-sweep/runs/20261031T120000Z-aaa/first-failure.log"))

    def test_latest_run_selected_without_mutating_older_results(self):
        old = self.add_run("20261031T120000Z-aaa", False)
        new = self.add_run("20261031T130000Z-bbb", True)
        with patch("sys.argv", ["package_p10_evidence.py"]):
            self.assertEqual(p.main(), 0)
        archive = next((self.root/"P10-RESULTS-TO-SEND").glob("*.zip"))
        with zipfile.ZipFile(archive) as z:
            manifest = json.loads(z.read("CHECKSUMS.json"))
            self.assertEqual(manifest["run_id"], new.name)
            self.assertTrue(manifest["qualified"])
        self.assertTrue((old/"consolidated.json").exists())
        self.assertEqual(p.select_run(old.name), old)


if __name__ == "__main__":
    unittest.main()
