"""P10 Windows/D3D12 native qualification. Each run preserves independent evidence.

python run_world_sweep.py --full
Native physics is never replaced by mocked results; missing tests imply NO-GO.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "evidence" / "p10" / "world-sweep"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
RUN = BASE / "runs" / RUN_ID
SOURCES = ("physics3.c", "physics3.h", "physics3.hlsl", "physics3-schema.json",
           "sunder_world.py", "headless_demo.py", "test_physics3.py",
           "test_sunder_world.py", "test_native_world.py", "test_world_sweep.py", "run_world_sweep.py",
           "package_p10_evidence.py", "test_p10_packaging.py",
           "RUN_P10_WINDOWS.cmd", "build_physics3.py")
CASES = ("cpu-world", "build", "world-empty", "native-world", "world-16",
         "world-1024", "native-physics", "legacy-pool-rail", "native-stress")


def digest():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}


def git_revision():
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                       capture_output=True, check=False)
    return p.stdout.strip() if p.returncode == 0 else None


def tracked_changes():
    try:
        p = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                           cwd=ROOT, capture_output=True, text=True,
                           timeout=15, check=False)
        return p.stdout.splitlines() if p.returncode == 0 else ["GIT STATUS UNAVAILABLE"]
    except (OSError, subprocess.TimeoutExpired):
        return ["GIT STATUS UNAVAILABLE"]


def driver_inventory():
    if platform.system() != "Windows":
        return {"status": "NOT RUN: no Windows GPU host"}
    cmd = ["powershell", "-NoProfile", "-Command",
           "Get-CimInstance Win32_VideoController | "
           "Select-Object Name,DriverVersion,PNPDeviceID | ConvertTo-Json -Compress"]
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=20)
        return json.loads(p.stdout) if p.returncode == 0 and p.stdout.strip() else {
            "status": "UNAVAILABLE", "error": p.stderr[-250:]}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"status": "UNAVAILABLE", "error": str(exc)}


def execute(name, args, result, timeout=600, output=None):
    start = time.perf_counter()
    legacy_root = ROOT / "dev-test-results"
    legacy_before = ({p.name for p in legacy_root.iterdir() if p.is_dir()}
                     if name == "legacy-pool-rail" and legacy_root.is_dir() else set())
    log = RUN / (name + ".log")
    env = os.environ.copy()
    env["SUNDER_P10_EVIDENCE_DIR"] = str(RUN)
    command = [sys.executable, *args]
    with log.open("w", encoding="utf-8") as f:
        try:
            process = subprocess.run(command, cwd=ROOT, env=env,
                                     stdout=f, stderr=subprocess.STDOUT,
                                     timeout=timeout, check=False)
            ok = process.returncode == 0
            failure = None if ok else "nonzero exit; inspect retained log"
            code = process.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            ok, code, failure = False, None, str(exc)
            f.write("\nRUNNER_EXCEPTION: " + str(exc) + "\n")
    row = {"name": name, "command": command, "exit_code": code,
           "status": "PASS" if ok else "FAIL", "failure": failure,
           "elapsed_wall_s": time.perf_counter() - start,
           "log": str(log.relative_to(ROOT))}
    if name == "native-world" and ok:
        try:
            native = json.loads((RUN / "native-world.json").read_text())
            if native.get("status") != "PASS" or native.get("not_run"):
                raise ValueError("native-world GPU cases incomplete")
            row["metrics"] = native.get("timing", {})
            row["adapter"] = native.get("adapters", [])
            row["cases"] = native.get("cases", [])
            row["output"] = str((RUN / "native-world.json").relative_to(ROOT))
        except (OSError, ValueError, KeyError) as exc:
            row.update(status="FAIL", failure="invalid native-world evidence: "+str(exc))
            ok = False
    if output is not None and ok:
        try:
            measured = json.loads(output.read_text())
            if measured.get("status") != "PASS":
                raise ValueError("native demo JSON does not report PASS")
            row["metrics"] = measured.get("summary", {})
            row["adapter"] = measured.get("adapter")
            row["interaction_class"] = measured.get("workload")
            row["replay"] = measured.get("replay")
            row["output"] = str(output.relative_to(ROOT))
            if not isinstance(row["replay"], dict) or not row["replay"].get(
                    "comparison", {}).get("equal"):
                raise ValueError("two accepted independent numerical replays missing")
            adapter = str(row["adapter"] or "").lower()
            if not adapter or any(x in adapter for x in (
                    "warp", "microsoft basic", "software", "llvmpipe", "swiftshader")):
                raise ValueError("hardware compute adapter unverified: " + adapter)
        except (OSError, ValueError, KeyError) as exc:
            row.update(status="FAIL", failure="invalid native evidence: " + str(exc))
            ok = False
    if name == "legacy-pool-rail" and legacy_root.is_dir():
        fresh = sorted((p for p in legacy_root.iterdir()
                        if p.is_dir() and p.name not in legacy_before))
        row["original_legacy_output"] = [str(p.relative_to(ROOT)) for p in fresh]
        try:
            for directory in fresh:
                destination = RUN / "legacy-dev-test" / directory.name
                shutil.copytree(directory, destination)
        except (OSError, shutil.Error) as exc:
            row.update(status="FAIL",
                       failure=f"could not retain original legacy evidence: {exc}")
            ok = False
    result["tests"].append(row)
    print(row["status"], name, flush=True)
    return ok


def main():
    if sys.argv[1:] != ["--full"]:
        print("Use exactly: python run_world_sweep.py --full", file=sys.stderr)
        return 2
    RUN.mkdir(parents=True, exist_ok=False)
    first = digest()
    revision = git_revision()
    dirty = tracked_changes()
    result = {
        "schema": "sunder-p10-native-qualification-v2",
        "run_id": RUN_ID, "status": "NO-GO", "pr": 8,
        "revision": revision, "tracked_changes_at_start": dirty,
        "host_platform": platform.platform(),
        "python": sys.version, "driver_inventory": driver_inventory(),
        "build_and_source_sha256": first,
        "scope": "native GPU authored spheres, independent numerical replay, old physics and separated-pair stress",
        "expected_cases": list(CASES), "tests": [],
        "unexecuted": list(CASES), "cpu_oracle_overhead": "separate native test results, not production timings",
        "stress_topology": "separated collision-bearing pairs, degree 1; not arbitrary connected authored world",
        "P9_bitwise": "INCOMPLETE / UNSUPPORTED",
        "handoff": "Double-click RUN_P10_WINDOWS.cmd; send latest ZIP in P10-RESULTS-TO-SEND",
        "production_release": "NOT QUALIFIED"
    }
    try:
        if platform.system() != "Windows":
            result["failure"] = "Windows x64 with functional D3D12 hardware adapter required"
            return 1
        tests = [
            ("cpu-world", ["-m", "unittest", "test_sunder_world", "test_p10_packaging",
                           "test_world_sweep", "-q"], 90, None),
            ("build", ["build_physics3.py"], 300, None),
            ("world-empty", ["headless_demo.py", "--capacity", "1", "--bodies",
                             "0", "--steps", "4", "--replay", "--out",
                             str(RUN / "world-empty.json")], 180, RUN / "world-empty.json"),
            ("native-world", ["test_native_world.py"], 240, None),
            ("world-16", ["headless_demo.py", "--capacity", "16", "--bodies",
                          "16", "--steps", "8", "--replay", "--out",
                          str(RUN / "world-16.json")], 180, RUN / "world-16.json"),
            ("world-1024", ["headless_demo.py", "--capacity", "1024", "--bodies",
                            "1024", "--steps", "8", "--replay", "--out",
                            str(RUN / "world-1024.json")], 300, RUN / "world-1024.json"),
            ("native-physics", ["test_physics3.py", "--smoke"], 300, None),
            ("legacy-pool-rail", ["dev_test.py", "full"], 1200, None),
            ("native-stress", ["test_physics3.py", "--stress",
                               "10000", "100000", "1000000"], 1800, None)
        ]
        for name, command, timeout, output in tests:
            ok = execute(name, command, result, timeout, output)
            result["unexecuted"].remove(name)
            if not ok:
                result["failure"] = "first failing gate: " + name
                return 1
        if result["unexecuted"]:
            return 1
        if first != digest():
            result["failure"] = "source inputs changed during qualification"
            return 1
        if not revision or dirty:
            result["failure"] = "missing Git provenance or locally modified tracked files"
            return 1
        result["status"] = "GO: all scripted native tests PASS; review limitations before merge"
        return 0
    finally:
        result["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        result["qualified"] = result["status"].startswith("GO:") and not result["unexecuted"]
        dest = RUN / "consolidated.json"
        dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        # Preserve the first canonical report. Subsequent runs have unique paths.
        canonical = BASE / "consolidated.json"
        if not canonical.exists():
            shutil.copy2(dest, canonical)
        with (BASE / "run-index.jsonl").open("a", encoding="utf-8") as index:
            index.write(json.dumps({"run": RUN_ID, "status": result["status"],
                                    "path": str(dest.relative_to(ROOT)),
                                    "revision": result["revision"]}) + "\n")
        print(json.dumps({"status": result["status"], "evidence": str(dest),
                          "failure": result.get("failure"),
                          "not_run": result["unexecuted"]}, indent=2), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
