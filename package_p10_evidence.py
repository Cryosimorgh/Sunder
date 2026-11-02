"""Package a single immutable P10 native qualification attempt for handoff.

Does not change test results. ZIP contains the selected run's original logs,
per-case measurements, D3D12 driver inventory, build manifest/logs, and a
checksum manifest so reviewers can detect tampering or missing files.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "evidence" / "p10" / "world-sweep"
BUILD = ROOT / "evidence" / "p10" / "build"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def select_run(run_id):
    root = BASE/"runs"
    if run_id:
        chosen = root/run_id
        if not chosen.is_dir() or chosen.parent != root:
            raise ValueError("invalid run ID or run directory unavailable")
        return chosen
    runs = sorted((p for p in root.glob("*") if p.is_dir() and
                   (p/"consolidated.json").is_file()), key=lambda p:p.name)
    if not runs:
        raise RuntimeError("no completed consolidated run found; run the suite first")
    return runs[-1]


def files_for_run(chosen):
    # Original per-case evidence is mandatory even for an incomplete run.
    for p in sorted(chosen.rglob("*")):
        if p.is_file():
            yield p
    if (BUILD/"manifest.json").is_file():
        yield BUILD/"manifest.json"
    for p in sorted(BUILD.glob("build-*.log")):
        yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--output-dir", default="P10-RESULTS-TO-SEND")
    opts = ap.parse_args()
    try:
        run = select_run(opts.run_id)
        result = json.loads((run/"consolidated.json").read_text(encoding="utf-8"))
        out_dir = ROOT / opts.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        # Never overwrite an earlier ZIP from this run.
        label = "GO" if result.get("qualified") else "NO-GO"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        name = f"Sunder-P10-{run.name}-{label}-{stamp}-{uuid.uuid4().hex[:6]}.zip"
        path = out_dir/name
        manifest = {
            "schema": "sunder-p10-windows-evidence-archive-v1",
            "run_id": run.name,
            "source_revision": result.get("revision"),
            "verdict": result.get("status"),
            "qualified": result.get("qualified", False),
            "files": {}
        }
        with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6) as archive:
            for original in files_for_run(run):
                data = original.read_bytes()
                rel = original.relative_to(ROOT).as_posix()
                archive.writestr(rel, data)
                manifest["files"][rel] = {"sha256": sha(data), "bytes": len(data)}
            note = (
                "P10 Windows qualification handoff\n\n"
                f"Run ID: {run.name}\n"
                f"Source revision: {result.get('revision')}\n"
                f"Verdict: {result.get('status')}\n"
                f"Qualified: {bool(result.get('qualified'))}\n\n"
                "Read the run-specific consolidated.json first. Other gates\n"
                "may not have executed after the first failure. Build success,\n"
                "virtual adapters and CPU mock tests do not qualify GPU physics.\n"
                "All archived files are listed with SHA-256 in CHECKSUMS.json.\n"
            )
            archive.writestr("READ_THIS_FIRST.txt", note)
            manifest["files"]["READ_THIS_FIRST.txt"] = {
                "sha256": sha(note.encode()), "bytes": len(note.encode())
            }
            archive.writestr("CHECKSUMS.json", json.dumps(manifest, indent=2)+"\n")
        print(json.dumps({"archive": str(path), "bytes": path.stat().st_size,
                          "qualified": manifest["qualified"],
                          "files": len(manifest["files"])}, indent=2))
        return 0
    except BaseException as error:
        print(f"Evidence packaging FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
