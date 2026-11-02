"""Headless Sunder capabilities demo: authored bodies, boundary edits and evidence.

Windows x64/D3D12 required. No viewer, fixture ID or hand-edited shader.
Usage: python build_physics3.py
       python headless_demo.py --capacity 16 --steps 8 --out evidence/p10/world-demo.json
       python headless_demo.py --capacity 1024 --steps 4 --replay
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import statistics
import time

from sunder_world import (Body, Handle, World, WorldConfig, WorldError,
                          compare_replays, replay_record)


def pct(values, q):
    if not values:
        return None
    s = sorted(values)
    at = (len(s) - 1) * q
    a = int(at)
    return s[a] + (s[min(a + 1, len(s) - 1)] - s[a]) * (at - a)


def summarize(rows):
    accepted = [r for r in rows if r.status == "ACCEPTED"]
    def stats(field):
        samples = [float(getattr(r, field)) for r in accepted]
        return {"samples": len(samples), "p50": pct(samples, .5),
                "p95": pct(samples, .95), "p99": pct(samples, .99),
                "worst": max(samples) if samples else None}
    return {"accepted": len(accepted),
            "rejected": len(rows) - len(accepted),
            "gpu_us": stats("gpu_us"),
            "cpu_production_thread_us": stats("cpu_us"),
            "host_wall_submission_completion_us": stats("wall_us"),
            "deadline_misses": sum(r.deadline_miss for r in rows),
            "gpu_fixed_step_deadline_misses": sum(r.gpu_fixed_step_deadline_miss for r in rows),
            "host_fixed_step_deadline_misses": sum(r.host_fixed_step_deadline_miss for r in rows),
            "peak_tracked_committed_bytes": max((r.committed_bytes for r in rows), default=0),
            "failures": [asdict(r) for r in rows if r.status != "ACCEPTED"],
            "cpu_oracle_overhead_us": "NOT MEASURED / independent native suite separate"}


def make_body(index):
    pair = index // 2
    center = (4. * (pair % 8), 4. * ((pair // 8) % 8),
              4. * (pair // 64))
    side = -1. if index % 2 == 0 else 1.
    return Body(position=(center[0] + .25 * side, center[1], center[2]),
                velocity=(-side, .0, .0), radius=.25, mass=1,
                restitution=.8, friction=.3)


def run(capacity, bodies, steps, replay, debug=False):
    cfg = WorldConfig(capacity=capacity, contact_capacity=max(64, capacity * 2),
                      iterations=128, debug=debug)
    results, inspections = [], []
    with World(cfg) as w:
        handles = [w.create_body(make_body(i)) for i in range(bodies)]
        if handles:
            w.apply_force(handles[0], (0., .1, 0.))
        if len(handles) >= 2:
            w.apply_impulse(handles[1], (-.1, 0., 0.))
        for step in range(steps):
            result = w.step()
            results.append(result)
            if result.status != "ACCEPTED":
                break
            with w.acquire() as snapshot:
                entries = list(snapshot.entries())
                inspections.append({"tick": snapshot.tick, "epoch": snapshot.epoch,
                                    "active": len(entries),
                                    "first": entries[0][1] if entries else None})
        if handles and len(results) == steps and results[-1].status == "ACCEPTED":
            old = handles[0]
            w.remove_body(old)
            replacement = w.create_body(make_body(0))
            if old == replacement:
                raise AssertionError("generation not incremented")
            results.append(w.step())
            if results[-1].status == "ACCEPTED":
                with w.acquire() as snapshot:
                    assert snapshot.body(replacement)
                    try:
                        snapshot.body(old)
                    except WorldError as error:
                        assert error.code == "STALE_HANDLE"
                    else:
                        raise AssertionError("stale handle accepted")
        record = w.record()
        report = {"status": "PASS" if results and all(r.status == "ACCEPTED" for r in results)
                  else "NO-GO", "config": asdict(cfg), "adapter": record["provenance"]["adapter"],
                  "source_provenance": record["provenance"], "summary": summarize(results),
                  "ticks": [asdict(r) for r in results],
                  "inspections": inspections,
                  "workload": "authored independently separated moving sphere pairs; full GPU interaction, not a storage-only scan",
                  "production_release": "NOT QUALIFIED"}
    if replay and report["status"] == "PASS":
        start = time.perf_counter_ns()
        a = replay_record(record)
        b = replay_record(record)
        comparison = compare_replays(a, b)
        report["replay"] = {"comparison": comparison, "two_native_runs": True,
                            "cpu_readback_comparison_us": (time.perf_counter_ns() - start) / 1000,
                            "bitwise": "UNSUPPORTED"}
        if not comparison["equal"]:
            report["status"] = "NO-GO"
    return report, record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capacity", type=int, default=16)
    parser.add_argument("--bodies", type=int, default=None)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("evidence/p10/world-demo.json"))
    args = parser.parse_args()
    if args.steps < 1 or args.steps > 128:
        parser.error("steps must be within [1,128]")
    bodies = args.capacity if args.bodies is None else args.bodies
    if bodies < 0 or bodies > args.capacity:
        parser.error("bodies must be within [0, capacity]")
    result = {"status": "NO-GO", "reason": "not started"}
    record = None
    try:
        result, record = run(args.capacity, bodies, args.steps, args.replay, args.debug)
    except Exception as e:
        result = {"status": "NO-GO", "failure_type": type(e).__name__,
                  "reason": str(e), "qualification": False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    if record is not None:
        args.out.with_name(args.out.stem + "-commands.json").write_text(
            json.dumps(record, indent=2))
    print(json.dumps({"status": result["status"], "evidence": str(args.out),
                      "summary": result.get("summary"), "reason": result.get("reason")},
                     indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
