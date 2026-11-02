"""One-click G7 Windows runner. Preserve all failures and always package a unique ZIP."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
SEND = ROOT / "G7-RESULTS-TO-SEND"
EVIDENCE = ROOT / "evidence" / "g7"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    try:
        p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                           text=True, timeout=20, check=False)
        return p.stdout.strip() if p.returncode == 0 else "UNAVAILABLE: " + p.stderr[-300:]
    except (OSError, subprocess.SubprocessError) as e:
        return "UNAVAILABLE: " + str(e)


def run(label, cmd, dest, timeout):
    output = dest / (label + ".log")
    result = {"name": label, "command": cmd, "log": output.name,
              "status": "NOT RUN", "exit_code": None}
    with output.open("w", encoding="utf-8") as log:
        try:
            proc = subprocess.run([sys.executable, *cmd], stdout=log, stderr=subprocess.STDOUT,
                                  cwd=ROOT, timeout=timeout, check=False)
            result["exit_code"] = proc.returncode
            result["status"] = "PASS" if proc.returncode == 0 else "FAIL"
        except (OSError, subprocess.TimeoutExpired) as exc:
            result.update(status="FAIL", reason=str(exc))
            log.write("\nRUNNER_FAILURE " + str(exc) + "\n")
    print(result["status"], label, flush=True)
    return result


def bundle(run_dir, stage, outcome):
    SEND.mkdir(parents=True, exist_ok=True)
    name = "Sunder-G7-" + stage + "-" + run_dir.name + ".zip"
    target = SEND / name
    if target.exists():
        raise FileExistsError("never overwrite a G7 handoff")
    payloads = {}
    for file in sorted(run_dir.rglob("*")):
        if file.is_file() and file.name != "MANIFEST.json":
            payloads[str(file.relative_to(run_dir))] = file
    manifest = {
        "schema": "sunder-g7-evidence-bundle-v1",
        "stage": stage, "run_id": run_dir.name,
        "result": outcome, "sha256": {key: sha(file) for key, file in payloads.items()},
        "source_commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
        "tracked_changes": git("status", "--porcelain", "--untracked-files=no"),
        "python": sys.version, "host": platform.platform(),
        "qualification": "GO requires actual native hardware correctness; ZIP alone never proves GO",
    }
    (run_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for key, file in payloads.items():
            z.write(file, key)
        z.write(run_dir / "MANIFEST.json", "MANIFEST.json")
    with zipfile.ZipFile(target) as z:
        for key, digest in manifest["sha256"].items():
            if hashlib.sha256(z.read(key)).hexdigest() != digest:
                raise AssertionError("ZIP verification failed: " + key)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true")
    mode.add_argument("--full", action="store_true")
    args = parser.parse_args(argv)
    stage = "quick" if args.quick else "full"
    uid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    directory = EVIDENCE / "launcher" / uid
    directory.mkdir(parents=True, exist_ok=False)
    status = {"stage": stage, "run_id": uid, "status": "NO-GO",
              "tested_sha": git("rev-parse", "HEAD"),
              "tracked_changes": git("status", "--porcelain", "--untracked-files=no"),
              "required": ["build_physics3", "g7_cpu_scene_contracts",
                           "p10_cpu_contracts", "g7_native_both", "p10_native_full"],
              "tests": [], "p10_native_full": "NOT RUN",
              "production_release": "NOT QUALIFIED"}
    package_error = None
    try:
        tasks = [
            ("build_physics3", ["build_physics3.py"], 600),
            ("g7_cpu_scene_contracts", ["-m", "unittest", "test_g7_scenarios", "-v"], 240),
            ("p10_cpu_contracts", ["-m", "unittest", "test_sunder_world",
                                   "test_p10_packaging", "test_world_sweep", "-v"], 600),
            ("g7_native_both", ["run_g7.py", "--scenario", "both",
                                 "--full" if stage == "full" else "--quick",
                                 "--output", str(EVIDENCE)], 7200),
        ]
        if stage == "full":
            tasks.append(("p10_native_full", ["run_world_sweep.py", "--full"], 7200))
        for name, command, timeout in tasks:
            before = {p.name for p in (EVIDENCE / "runs").iterdir()} if (EVIDENCE / "runs").is_dir() else set()
            p10_dir = ROOT / "evidence/p10/world-sweep/runs"
            p10_before = ({p.name for p in p10_dir.iterdir() if p.is_dir()}
                          if name == "p10_native_full" and p10_dir.is_dir() else set())
            result = run(name, command, directory, timeout)
            status["tests"].append(result)
            if name == "g7_native_both":
                after = list((EVIDENCE / "runs").iterdir()) if (EVIDENCE / "runs").is_dir() else []
                fresh = [p for p in after if p.name not in before and p.is_dir()]
                if len(fresh) != 1:
                    result["status"] = "FAIL"
                    result["reason"] = f"expected one new native evidence directory, found {len(fresh)}"
                else:
                    latest = fresh[0]
                    status["native_evidence_folder"] = str(latest.relative_to(ROOT))
                    for file in latest.rglob("*"):
                        if file.is_file():
                            rel = Path("g7-native") / file.relative_to(latest)
                            dest = directory / rel
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(file.read_bytes())
            if name == "p10_native_full":
                status["p10_native_full"] = result["status"]
                p10_fresh = ([p for p in p10_dir.iterdir()
                              if p.is_dir() and p.name not in p10_before]
                             if p10_dir.is_dir() else [])
                if len(p10_fresh) != 1:
                    result["status"] = "FAIL"
                    result["reason"] = f"expected one fresh original P10 evidence directory; found {len(p10_fresh)}"
                else:
                    status["p10_evidence_folder"] = str(p10_fresh[0].relative_to(ROOT))
                    for file in p10_fresh[0].rglob("*"):
                        if file.is_file():
                            dest = directory / "p10-native" / file.relative_to(p10_fresh[0])
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(file.read_bytes())
        status["source_and_build_sha256"] = {
            str(f.relative_to(ROOT)): sha(f)
            for f in [ROOT / "physics3.c", ROOT / "physics3.h", ROOT / "physics3.hlsl",
                      ROOT / "sunder_world.py", ROOT / "run_g7.py", ROOT / "g7_scenarios.py",
                      ROOT / "evidence/p10/build/physics3.dll",
                      ROOT / "evidence/p10/build/manifest.json"] if f.is_file()}
        if (stage == "full" and not status["tracked_changes"] and
                all(t["status"] == "PASS" for t in status["tests"])):
            status["status"] = "PENDING_ADVERSARIAL_REVIEW"
        else:
            status["status"] = "NO-GO"
        if stage == "quick":
            status["not_run"] = ["P10 native full", "G7 10K", "G7 100K"]
    except BaseException as error:
        status["status"] = "NO-GO"
        status["runner_failure"] = f"{type(error).__name__}: {error}"
        status["traceback"] = traceback.format_exc(limit=10)
    finally:
        (directory / "RUN-RESULT.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        try:
            target = bundle(directory, stage, status)
        except BaseException as error:
            package_error = str(error)
            (directory / "PACKAGING-FAILURE.txt").write_text(package_error, encoding="utf-8")
            print("PACKAGING ERROR; preserve evidence directory:", package_error, flush=True)
        else:
            print("SEND EXACTLY THIS ZIP:", target, flush=True)
        print(json.dumps({"status": status["status"], "stage": stage,
                          "package_error": package_error}, indent=2))
    return 0 if status["status"] == "PENDING_ADVERSARIAL_REVIEW" and package_error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
