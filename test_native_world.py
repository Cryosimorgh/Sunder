"""Actual Windows D3D12 application-world acceptance checks. Never uses FakeGPU.

Executed as one gate by run_world_sweep.py --full. Native oracle and historical
stress/legacy suites are separate mandatory gates. No thresholds are relaxed.
"""
from __future__ import annotations

from dataclasses import asdict
import ctypes as C
import json
import math
import os
from pathlib import Path
import platform
import time
import traceback

import numpy as np

from sunder_world import (Backend, Body, Handle, NativeResult, World, WorldConfig,
                          WorldError, compare_replays, replay_record)

OUT = Path(os.environ.get("SUNDER_P10_EVIDENCE_DIR", "evidence/p10/world-sweep"))
RESULTS = []
TICKS = []
ADAPTERS = set()
EPS = 2e-5


def ensure(condition, message):
    if not condition:
        raise AssertionError(message)


def near(actual, expected, tol=EPS):
    ensure(np.allclose(actual, expected, rtol=tol, atol=tol),
           f"value mismatch: actual={actual}, expected={expected}")


def tick(world, status="ACCEPTED"):
    result = world.step()
    TICKS.append(asdict(result))
    ensure(result.status == status,
           f"tick status {result.status}; expected {status}; cause={result.cause}; "
           f"gpu_flags={result.error_bits}")
    return result


def world(config):
    w = World(config)
    ADAPTERS.add(w._backend.adapter)
    name = w._backend.adapter.lower()
    ensure(name and not any(x in name for x in
           ("warp", "microsoft basic", "hyper-v video", "software", "llvmpipe",
            "swiftshader")), f"no qualified physical GPU adapter: {name}")
    return w


def case_authored_lifecycle():
    with world(WorldConfig(capacity=3, contact_capacity=16)) as w:
        first = w.create_body(Body((0., 0., 0.)))
        second = w.create_body(Body((4., 0., 0.), static=True))
        ensure(tick(w).active == 2, "initial authored count")
        with w.acquire() as snap:
            near(snap.body(first)["position"], (0, 0, 0))
            ensure(snap.body(second)["static"], "static policy")
            ensure(snap.epoch == 1 and snap.tick == 1, "snapshot metadata")
        w.update_body(first, velocity=(.5, 0, 0), restitution=.5)
        tick(w)
        with w.acquire() as snap:
            near(snap.body(first)["velocity"], (.5, 0, 0))
            near(snap.body(first)["restitution"], .5)
        old = first
        w.remove_body(old)
        fresh = w.create_body(Body((0., 2., 0.)))
        ensure(old.slot == fresh.slot and old.generation != fresh.generation,
               "generation reuse")
        with_error = False
        try:
            w.apply_force(old, (1, 0, 0))
        except WorldError as e:
            with_error = e.code == "STALE_HANDLE"
        ensure(with_error, "stale handle accepted")
        tick(w)
        with w.acquire() as snap:
            near(snap.body(fresh)["position"], (0, 2, 0))
            ensure(len(list(snap.entries())) == 2, "active count after reuse")
        before = (w.tick_id, w.epoch)
        held = w.acquire()
        try:
            try:
                w.grow(6)
                raise AssertionError("growth admitted with outstanding lease")
            except WorldError as e:
                ensure(e.code == "BACKPRESSURE", "growth lease classifier")
            ensure((w.tick_id, w.epoch) == before, "rejected growth altered clock")
        finally:
            held.close()
        w.grow(6)
        ensure((w.tick_id, w.epoch) == (before[0], before[1] + 1),
               "growth clock/epoch")
        newer = w.create_body(Body((0., 4., 0.)))
        r = tick(w)
        with w.acquire() as snap:
            near(snap.body(fresh)["position"], (0, 2, 0))
            near(snap.body(newer)["position"], (0, 4, 0))
            ensure(len(list(snap.entries())) == 3, "post-growth active count")
            ensure(snap.tick == r.tick, "native/world tick after growth")


def case_force_gravity_impulse():
    cfg = WorldConfig(capacity=1, contact_capacity=8, gravity=(0., -9.81, 0.))
    with world(cfg) as w:
        h = w.create_body(Body((0., 3., 0.), mass=2.))
        w.apply_force(h, (4., 0., 0.))
        w.apply_impulse(h, (2., 0., 0.))
        tick(w)
        with w.acquire() as snap:
            v = snap.body(h)["velocity"]
            near(v, (1 + 2*cfg.dt, -9.81*cfg.dt, 0), tol=4e-5)
            near(snap.body(h)["position"][:2],
                 (v[0]*cfg.dt, 3 + v[1]*cfg.dt), tol=4e-5)
        w.clear_force(h)
        tick(w)
        with w.acquire() as snap:
            near(snap.body(h)["velocity"][0], 1 + 2*cfg.dt, tol=4e-5)


def case_collision_friction():
    cfg = WorldConfig(capacity=2, contact_capacity=16)
    with world(cfg) as w:
        a = w.create_body(Body((-.25, 0., 0.), (1., .4, .2),
                               restitution=.8, friction=.35))
        b = w.create_body(Body((.25, 0., 0.), (-1., 0., 0.),
                               restitution=.8, friction=.35))
        p0 = np.array((0., .4, .2))
        e0 = .5 * (1 + .4**2 + .2**2 + 1)
        r = tick(w)
        ensure(r.contacts >= 1, "no sphere-sphere contact")
        with w.acquire() as snap:
            x, y = snap.body(a), snap.body(b)
            p1 = np.asarray(x["velocity"]) + np.asarray(y["velocity"])
            near(p1, p0, tol=5e-5)
            inertia = .4 * .25**2
            e1 = sum(.5*np.dot(q["velocity"], q["velocity"]) +
                     .5*inertia*np.dot(q["angular_velocity"], q["angular_velocity"])
                     for q in (x, y))
            ensure(e1 <= e0 + 3e-5, f"passive collision energy gain {e1-e0}")
            ensure(np.linalg.norm(x["angular_velocity"]) > .01,
                   "frictional spin missing")
            ensure(x["position"][0] + .25 <= y["position"][0] - .25 + 3e-5,
                   "interpenetration after accepted tick")


def case_sleep_wake():
    with world(WorldConfig(capacity=1, contact_capacity=8)) as w:
        h = w.create_body(Body((0, 0, 0), restitution=0.))
        tick(w)
        for _ in range(34):
            tick(w)
        with w.acquire() as snap:
            ensure(snap.body(h)["sleep_frames"] >= 32., "body failed to sleep")
        w.apply_impulse(h, (1., 0., 0.))
        tick(w)
        with w.acquire() as snap:
            ensure(snap.body(h)["sleep_frames"] == 0., "body failed to wake")
            ensure(snap.body(h)["velocity"][0] > .9, "wake impulse lost")


def case_snapshot_backpressure():
    with world(WorldConfig(capacity=2, contact_capacity=8)) as w:
        h = w.create_body(Body((0, 0, 0)))
        tick(w)
        leases = []
        try:
            for index in range(3):
                if index:
                    tick(w)
                leases.append(w.acquire())
            before = (w.tick_id, w.epoch)
            tick(w, "BACKPRESSURE")
            ensure((w.tick_id, w.epoch) == before, "backpressure advanced world")
            ensure(len(leases) == 3, "missing native leases")
        finally:
            for lease in reversed(leases):
                lease.close()
        tick(w)
        with w.acquire() as snap:
            near(snap.body(h)["position"], (0, 0, 0))


class InjectRejectionOnce(Backend):
    reject_next = False

    def tick(self):
        if not self.reject_next:
            return super().tick()
        self.reject_next = False
        result = NativeResult()
        g = np.asarray(self.cfg.gravity, dtype=np.float32)
        ok = bool(self.dll.ph3_tick(self.ptr, np.float32(self.cfg.dt),
                                    g.ctypes.data, np.float32(self.cfg.cell_size),
                                    1, C.byref(result)))
        return ok, result


def case_staged_rejection_and_recovery():
    cfg = WorldConfig(capacity=2, contact_capacity=16)
    with World(cfg, backend_factory=InjectRejectionOnce) as w:
        ADAPTERS.add(w._backend.adapter)
        first = w.create_body(Body((0, 0, 0)))
        tick(w)
        with w.acquire() as before:
            accepted = before.body(first)
            old_tick_epoch = (before.tick, before.epoch)
        w.remove_body(first)
        rejected_id = w.create_body(Body((0, 1, 0)))
        w._backend.reject_next = True
        result = tick(w, "REJECTED")
        ensure(result.error_bits & 16, "injected GPU validation bit absent")
        ensure((w.tick_id, w.epoch) == old_tick_epoch, "rejected tick was published")
        with w.acquire() as snapshot:
            ensure(snapshot.body(first) == accepted, "failed tick changed accepted state")
            try:
                snapshot.body(rejected_id)
                raise AssertionError("provisional body exposed")
            except WorldError as e:
                ensure(e.code == "STALE_HANDLE", "wrong stale-handle classifier")
        w.remove_body(first)
        next_id = w.create_body(Body((0, 2, 0)))
        ensure(next_id.generation > rejected_id.generation,
               "rejected candidate handle reused")
        tick(w)
        with w.acquire() as snapshot:
            near(snapshot.body(next_id)["position"], (0, 2, 0))


def case_invalid_commands_and_worlds():
    with world(WorldConfig(capacity=2, contact_capacity=8)) as left, \
         world(WorldConfig(capacity=2, contact_capacity=8)) as right:
        a = left.create_body(Body((0, 0, 0)))
        b = right.create_body(Body((1, 0, 0)))
        for fn in (
            lambda: left.create_body(Body((0, 0, 0), mass=-1)),
            lambda: left.create_body(Body((600, 0, 0))),
            lambda: left.create_body(Body((0, 0, 0), velocity=(math.nan, 0, 0))),
            lambda: right.remove_body(a),
            lambda: left.apply_impulse(b, (1, 0, 0)),
        ):
            try:
                fn()
                raise AssertionError("invalid command accepted")
            except WorldError:
                pass
        tick(left)
        tick(right)
        with left.acquire() as snap:
            ensure(len(list(snap.entries())) == 1, "invalid command published")
        with right.acquire() as snap:
            near(snap.body(b)["position"], (1, 0, 0))


def case_two_independent_replays():
    cfg = WorldConfig(capacity=3, contact_capacity=24)
    with world(cfg) as w:
        a = w.create_body(Body((-.25, 0, 0), (1, .2, 0), friction=.35))
        b = w.create_body(Body((.25, 0, 0), (-1, 0, 0), friction=.35))
        tick(w)
        w.apply_force(a, (0, .1, 0))
        tick(w)
        w.clear_force(a)
        w.update_body(b, restitution=.6)
        tick(w)
        recording = w.record()
    start = time.perf_counter()
    native_first = replay_record(recording)
    native_second = replay_record(recording)
    comparison = compare_replays(native_first, native_second)
    ensure(comparison["equal"], f"first numeric divergence: {comparison['first_divergence']}")
    ensure(len(native_first) == 3 and len(native_second) == 3,
           "incomplete independent replay")
    return {"two_distinct_native_world_runs": True, "comparison": comparison,
            "elapsed_including_readback_and_comparison_s": time.perf_counter()-start,
            "bitwise_replay": "UNSUPPORTED"}


def summarise():
    accepted = [x for x in TICKS if x["status"] == "ACCEPTED"]
    def pct(field):
        x = sorted(float(t[field]) for t in accepted)
        if not x:
            return None
        def q(v):
            p = (len(x)-1)*v
            n = int(p)
            return x[n] + (x[min(n+1, len(x)-1)]-x[n])*(p-n)
        return {"count": len(x), "p50": q(.5), "p95": q(.95),
                "p99": q(.99), "worst": x[-1]}
    return {
        "accepted_ticks": len(accepted),
        "rejected_ticks": len(TICKS)-len(accepted),
        "expected_rejections": [x for x in TICKS if x["status"] != "ACCEPTED"],
        "gpu_us": pct("gpu_us"), "cpu_thread_us": pct("cpu_us"),
        "submission_completion_wall_us": pct("wall_us"),
        "gpu_dt_misses": sum(t["gpu_fixed_step_deadline_miss"] for t in TICKS),
        "host_dt_misses": sum(t["host_fixed_step_deadline_miss"] for t in TICKS),
        "tracked_committed_peak_bytes": max((x["committed_bytes"] for x in TICKS), default=0),
        "note": "CPU oracle overhead is not included; independent native solver oracle is a separate gate."
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"schema": "p10-native-world-gpu-v1", "status": "NO-GO",
              "platform": platform.platform(), "cases": [], "adapters": [],
              "timing": None, "failure": None, "not_gpu_mock": True}
    cases = [
        ("authored_lifecycle_growth", case_authored_lifecycle),
        ("gravity_force_impulse", case_force_gravity_impulse),
        ("collision_friction", case_collision_friction),
        ("sleep_wake", case_sleep_wake),
        ("three_snapshot_backpressure", case_snapshot_backpressure),
        ("staged_rejection_and_recovery", case_staged_rejection_and_recovery),
        ("invalid_commands_world_isolation", case_invalid_commands_and_worlds),
        ("two_independent_native_replays", case_two_independent_replays),
    ]
    try:
        if platform.system() != "Windows":
            raise RuntimeError("native test requires Windows x64 D3D12 device")
        for name, run in cases:
            started = time.perf_counter()
            record = {"name": name, "status": "FAIL"}
            try:
                details = run()
                record.update(status="PASS", wall_seconds=time.perf_counter()-started,
                              details=details)
            except BaseException:
                record.update(wall_seconds=time.perf_counter()-started,
                              failure=traceback.format_exc())
                report["failure"] = name
                report["cases"].append(record)
                break
            report["cases"].append(record)
            print("PASS", name, flush=True)
        report["status"] = "PASS" if len(report["cases"]) == len(cases) and all(
            x["status"] == "PASS" for x in report["cases"]) else "NO-GO"
    except BaseException:
        report["failure"] = traceback.format_exc()
    finally:
        report["not_run"] = [name for name, _ in cases
                             if name not in [c["name"] for c in report["cases"]]]
        report["adapters"] = sorted(ADAPTERS)
        report["timing"] = summarise()
        report["tick_results"] = TICKS
        dest = OUT/"native-world.json"
        dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "evidence": str(dest),
                          "failure": report["failure"], "not_run": report["not_run"]}),
              flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
