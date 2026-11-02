"""G7: real D3D12 world-API cube/belt workload and explicitly sampled diagnostics.

No fake backend, CPU solver, silent body reduction, or hot-loop full snapshots.
Use --quick for a bounded smoke run; --full requires native Windows hardware.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import traceback
import uuid

import numpy as np

from g7_scenarios import SceneSpec, SceneAdmissionError, authored_hash, generate
from sunder_world import Body, World, WorldConfig, WorldError


ROOT = Path(__file__).resolve().parent
FIELDS = ("status", "tick", "epoch", "error_bits", "contacts", "active", "gpu_us",
          "cpu_us", "committed_bytes", "deadline_miss", "cause", "wall_us",
          "gpu_fixed_step_deadline_miss", "host_fixed_step_deadline_miss",
          "gpu_candidates", "gpu_max_degree", "candidate_stage_us",
          "native_submit_completion_us")


def percentile(data, p):
    if not data:
        return None
    a = sorted(float(x) for x in data)
    j = (len(a) - 1) * p
    low = int(j)
    return a[low] + (a[min(len(a)-1, low+1)] - a[low]) * (j-low)


def stats(rows, name):
    values = [float(r[name]) for r in rows if r["status"] == "ACCEPTED"]
    return {"count": len(values), "p50": percentile(values, .5),
            "p95": percentile(values, .95), "p99": percentile(values, .99),
            "worst": max(values) if values else None}


def source_hashes():
    names = ("g7_scenarios.py", "run_g7.py", "sunder_world.py", "physics3.c",
             "physics3.h", "physics3.hlsl", "physics3-schema.json", "build_physics3.py")
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in names if (ROOT / p).exists()}


def revision():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                       text=True, timeout=10, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return "UNAVAILABLE"


def hardware_inventory():
    info = {"platform": platform.platform(), "python": sys.version,
            "native_windows_d3d12": os.name == "nt"}
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15, check=False)
            info["video_controllers"] = proc.stdout.strip() if proc.returncode == 0 else proc.stderr[-300:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            info["inventory_error"] = str(exc)
    return info


def topology(contacts, body_belts, active_count, previous):
    # Speculative future contacts do not count as observed impacts.
    parents = list(range(active_count))
    sizes = [1] * active_count
    degree = [0] * active_count

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    actual = set()
    cross = 0
    overlapping = 0
    impulsive = 0
    for rec in contacts:
        a, b = int(rec["a"]), int(rec["b"])
        if not (0 <= a < active_count and 0 <= b < active_count) or a == b:
            raise ValueError(f"invalid native contact indices: {a}, {b}")
        gap, impulse = float(rec["gap"]), float(rec["normal_impulse"])
        if not (math.isfinite(gap) and math.isfinite(impulse)):
            raise ValueError("nonfinite native contact readback")
        if gap <= 0:
            overlapping += 1
        if impulse > 0:
            impulsive += 1
        if gap > 0 and impulse <= 0:
            continue
        edge = (min(a, b), max(a, b))
        actual.add(edge)
        degree[a] += 1
        degree[b] += 1
        if body_belts[a] != -1 and body_belts[a] != body_belts[b]:
            cross += 1
        pa, pb = root(a), root(b)
        if pa != pb:
            if sizes[pa] < sizes[pb]:
                pa, pb = pb, pa
            parents[pb] = pa
            sizes[pa] += sizes[pb]
    roots = {root(i) for i in range(active_count)}
    result = {"native_speculative_contacts": len(contacts),
              "overlapping_contacts": overlapping, "positive_impulse_contacts": impulsive,
              "observed_edges": len(actual), "cross_belt_edges": cross,
              "components_including_isolates": len(roots),
              "largest_island": max((sizes[i] for i in roots), default=0),
              "max_degree": max(degree, default=0),
              "degree_p50": percentile(degree, .5), "degree_p95": percentile(degree, .95),
              "contact_churn_since_previous_sample": None if previous is None
              else len(actual.symmetric_difference(previous)),
              "churn_is_consecutive_tick": False}
    return result, actual


def final_state(world, handles):
    start = time.perf_counter_ns()
    with world.acquire() as snapshot:
        state = []
        for handle in handles:
            b = snapshot.body(handle)
            values = (*b["position"], *b["velocity"])
            if not all(math.isfinite(x) for x in values):
                raise ValueError(f"nonfinite final state in slot {handle.slot}")
            state.append(values)
    return {"values": state, "diagnostic_readback_us":
            (time.perf_counter_ns() - start) / 1000}


def compare_states(a, b, tol=2e-4):
    if len(a) != len(b):
        return {"equal": False, "first_divergence": "body counts differ"}
    maximum = 0.
    for i, (left, right) in enumerate(zip(a, b)):
        for j, (x, y) in enumerate(zip(left, right)):
            err = abs(x-y)
            maximum = max(maximum, err)
            if err > tol * max(1., abs(x), abs(y)):
                return {"equal": False, "first_divergence": {"body": i, "field": j,
                        "left": x, "right": y, "absolute_error": err},
                        "abs_tolerance_scale": tol}
    return {"equal": True, "max_abs_error": maximum,
            "bitwise": "UNSUPPORTED", "abs_tolerance_scale": tol}


def case(spec, args, directory, repeat):
    directory.mkdir(parents=True, exist_ok=False)
    report = {"status": "NO-GO", "scenario": asdict(spec), "repeat": repeat,
              "source_sha256": source_hashes(), "source_commit": revision(),
              "hardware": hardware_inventory(), "case_dir": str(directory),
              "requirement": "native D3D12, not fake GPU; spheres only, no self-gravity"}
    state = None
    rows, samples = [], []
    try:
        if os.name != "nt":
            raise RuntimeError("NOT RUN: real Windows x64 D3D12 is required")
        params, stream = generate(spec)
        report["scene_parameters"] = params
        candidate_budget = args.contact_budget if args.contact_budget else max(128, 4 * spec.bodies)
        capacity = spec.bodies
        estimate = capacity * 1500 + candidate_budget * 128 + 16 * 1024 * 1024
        report["conservative_admission_estimate_bytes"] = estimate
        if estimate > args.max_committed_mib * 1024**2:
            raise SceneAdmissionError("NO-GO: conservative committed-memory estimate exceeds configured MiB limit")
        if spec.bodies > 100_000 and not args.allow_large:
            raise SceneAdmissionError("NOT RUN: >100K bodies require explicit --allow-large")
        cfg = WorldConfig(capacity=capacity, contact_capacity=candidate_budget,
                          iterations=args.iterations, dt=args.dt, gravity=tuple(args.gravity),
                          cell_size=args.cell_size, deadline_ms=args.deadline_ms)
        report["world_config"] = asdict(cfg)
        start = time.perf_counter_ns()
        particles = list(stream)
        generation_us = (time.perf_counter_ns() - start) / 1000
        if len(particles) != spec.bodies:
            raise SceneAdmissionError(f"authored {len(particles)} of {spec.bodies}: no silent drops allowed")
        report["scene_hash"] = authored_hash(particles)
        report["cpu_scene_authoring_us"] = generation_us
        report["created_attempts"] = 0
        report["created_author_handles"] = 0
        report["accepted_body_count"] = 0
        report["rejected_body_count"] = 0
        report["phase_stats"] = {}
        handles = []
        body_belts = []
        prior = None
        first_cross_tick = None
        peak_cross = 0
        peak_island = 0
        maximum_overlap = 0
        last_sample_tick = -1
        fill_start = time.perf_counter_ns()
        with World(cfg) as world, (directory / "ticks.csv").open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, FIELDS)
            writer.writeheader()
            # Cube bodies remain motionless during staged insertion. Only after
            # capacity is accepted do inward velocities start, avoiding overlaps
            # between previously moved particles and newly authored particles.
            total = max(args.duration_ticks, math.ceil(spec.bodies / args.spawn_batch) + args.post_full_ticks) if spec.scenario == "cube" else args.duration_ticks
            cursor = 0
            for frame in range(total):
                count = (min(args.spawn_batch, spec.bodies - cursor)
                         if spec.scenario == "cube" else spec.bodies - cursor)
                edit_start = time.perf_counter_ns()
                for particle in particles[cursor:cursor+count]:
                    report["created_attempts"] += 1
                    body = particle.body
                    if spec.scenario == "cube":
                        body = replace(body, velocity=(0., 0., 0.))
                    handle = world.create_body(body)
                    handles.append(handle)
                    body_belts.append(particle.belt)
                    report["created_author_handles"] += 1
                cursor += count
                if (spec.scenario == "cube" and report.get("fill_tick") is not None and
                    frame == report["fill_tick"]):
                    for handle, particle in zip(handles, particles):
                        world.update_body(handle, velocity=particle.body.velocity)
                cpu_edits_us = (time.perf_counter_ns() - edit_start) / 1000
                result = world.step()
                row = asdict(result)
                writer.writerow({k: row.get(k) for k in FIELDS})
                rows.append(dict(row, frame=frame, cpu_command_authoring_us=cpu_edits_us))
                if result.status != "ACCEPTED":
                    report["failure"] = f"frame {frame}: {result.status}: {result.cause}; bits={result.error_bits}"
                    break
                if result.active != cursor:
                    raise AssertionError(f"active count {result.active} != authored accepted {cursor}")
                report["accepted_body_count"] = cursor
                if cursor == spec.bodies and "fill_tick" not in report:
                    report["fill_tick"] = frame + 1
                    report["seconds_to_fill"] = (time.perf_counter_ns() - fill_start) / 1e9
                sample = (frame % args.sample_every == 0 or frame == total-1 or
                          (spec.scenario == "cube" and frame + 1 == report.get("fill_tick")))
                if sample:
                    diagnostic_start = time.perf_counter_ns()
                    contacts = world.diagnostic_contacts(result.contacts)
                    shape, prior = topology(contacts, body_belts, result.active, prior)
                    sample_us = (time.perf_counter_ns() - diagnostic_start) / 1000
                    shape.update(frame=frame, accepted_tick=result.tick, readback_and_topology_us=sample_us,
                                 after_full_ticks=max(0, result.tick-report.get("fill_tick", total)),
                                 churn_is_consecutive_tick=(last_sample_tick == frame-1))
                    samples.append(shape)
                    last_sample_tick = frame
                    peak_cross = max(peak_cross, shape["cross_belt_edges"])
                    peak_island = max(peak_island, shape["largest_island"])
                    maximum_overlap = max(maximum_overlap, shape["overlapping_contacts"])
                    if first_cross_tick is None and shape["cross_belt_edges"] > 0:
                        first_cross_tick = result.tick
                if result.committed_bytes > args.max_committed_mib * 1024**2:
                    report["failure"] = "NO-GO: actual committed memory exceeded configured limit"
                    break
            report["ticks_executed"] = len(rows)
            report["post_full_ticks_accepted"] = max(0, result.tick - report.get("fill_tick", total))
            report["adapter"] = world.record()["provenance"]["adapter"]
            report["build_provenance"] = world.record()["provenance"]["sha256"]
            if (len(rows) == total and all(x["status"] == "ACCEPTED" for x in rows)
                and report["accepted_body_count"] == spec.bodies):
                state = final_state(world, handles)
                report["final_state_diagnostic_us"] = state["diagnostic_readback_us"]
        report["actual_peak_tracked_committed_bytes"] = max((r["committed_bytes"] for r in rows), default=0)
        report["samples"] = len(samples)
        report["phase_stats"] = {
            "gpu_native_us": stats(rows, "gpu_us"),
            "host_submit_completion_us": stats(rows, "native_submit_completion_us"),
            "cpu_native_thread_us": stats(rows, "cpu_us"),
            "host_total_step_us": stats(rows, "wall_us"),
            "candidate_staging_us": stats(rows, "candidate_stage_us"),
            "cpu_author_edits_us": stats(rows, "cpu_command_authoring_us"),
            "contacts": stats(rows, "contacts"), "candidates": stats(rows, "gpu_candidates")}
        report["deadline_misses"] = sum(x["deadline_miss"] for x in rows)
        report["gpu_fixed_step_deadline_misses"] = sum(x["gpu_fixed_step_deadline_miss"] for x in rows)
        report["host_fixed_step_deadline_misses"] = sum(x["host_fixed_step_deadline_miss"] for x in rows)
        report["peak_cross_belt_edges"] = peak_cross
        report["peak_largest_contact_island"] = peak_island
        report["peak_overlapping_contacts"] = maximum_overlap
        report["first_cross_belt_contact_tick"] = first_cross_tick
        report["contact_graph_qualification"] = ("observed cross-belt impacts and nontrivial island"
            if spec.scenario == "belts" and peak_cross and peak_island >= 3 else
            "observed dense contact graph" if spec.scenario == "cube"
            and spec.preset == "dense" and maximum_overlap and peak_island >= 3 else
            "NOT DEMONSTRATED")
        adapter = str(report.get("adapter", "")).lower()
        physical = bool(adapter) and not any(x in adapter for x in
                      ("warp", "microsoft basic", "hyper-v", "software", "llvmpipe"))
        graph_ok = (peak_cross > 0 and peak_island >= 3) if spec.scenario == "belts" else (
            maximum_overlap > 0 and peak_island >= 3 if spec.preset == "dense" else True)
        enough_post = (spec.scenario != "cube" or
                       report["post_full_ticks_accepted"] >= args.post_full_ticks)
        if state is not None and physical and graph_ok and enough_post:
            report["status"] = "PASS"
        else:
            report.setdefault("failure", "scene, timing, hardware or contact qualification incomplete")
        if state is not None:
            report["final_state_values"] = state["values"]
    except BaseException as exc:
        report["status"] = "NO-GO"
        report["failure"] = f"{type(exc).__name__}: {exc}"
        report["exception_traceback"] = traceback.format_exc(limit=8)
    finally:
        with (directory / "samples.jsonl").open("w", encoding="utf-8") as file:
            for sample in samples:
                file.write(json.dumps(sample) + "\n")
        with (directory / "ticks.jsonl").open("w", encoding="utf-8") as file:
            for tick in rows:
                file.write(json.dumps(tick) + "\n")
        audit = {k: v for k, v in report.items() if k != "final_state_values"}
        (directory / "case.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", choices=("cube", "belts", "both"), default="both")
    ap.add_argument("--preset", choices=("isolated", "moderate", "dense"), default="dense")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--bodies", type=int, default=1000)
    ap.add_argument("--duration-ticks", type=int, default=96)
    ap.add_argument("--post-full-ticks", type=int, default=64)
    ap.add_argument("--spawn-batch", type=int, default=4096)
    ap.add_argument("--sample-every", type=int, default=8)
    ap.add_argument("--contact-budget", type=int, default=0)
    ap.add_argument("--iterations", type=int, default=128)
    ap.add_argument("--dt", type=float, default=1/128)
    ap.add_argument("--cell-size", type=float, default=2.)
    ap.add_argument("--gravity", type=float, nargs=3, default=(0., 0., 0.))
    ap.add_argument("--deadline-ms", type=float, default=16.)
    ap.add_argument("--radius", type=float, default=.4)
    ap.add_argument("--mass", type=float, default=1.)
    ap.add_argument("--cube-size", type=float)
    ap.add_argument("--closing-speed", type=float, default=16.)
    ap.add_argument("--spin-speed", type=float, default=.055)
    ap.add_argument("--counter-rotate", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--max-committed-mib", type=int, default=2048)
    ap.add_argument("--allow-large", action="store_true")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--quick", action="store_true")
    group.add_argument("--full", action="store_true")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--output", type=Path, default=ROOT / "evidence/g7")
    args = ap.parse_args(argv)
    if (min(args.duration_ticks, args.post_full_ticks, args.spawn_batch,
            args.sample_every, args.repeats, args.max_committed_mib) < 1
            or args.contact_budget < 0):
        ap.error("positive tick, post-full, batch, sample, repeat, memory and contact-budget required")
    scales = [1000, 10000, 100000] if args.full else [args.bodies]
    if args.quick and args.bodies == 1000:
        args.duration_ticks = min(args.duration_ticks, 64)
        args.post_full_ticks = min(args.post_full_ticks, 32)
    uid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    folder = args.output / "runs" / uid
    folder.mkdir(parents=True, exist_ok=False)
    reports, comparisons = [], []
    result = {"schema": "sunder-g7-native-dense-v1", "run_id": uid,
              "status": "NO-GO", "qualification": "unverified until native hardware acceptance",
              "branch_role": "implementation evidence, not final PR gate",
              "required_scenarios": ["cube", "belts"], "arguments": vars(args).copy(),
              "cases": [], "numerical_replays": [],
              "source_sha256": source_hashes(), "source_commit": revision(),
              "hardware": hardware_inventory()}
    result["arguments"]["output"] = str(args.output)
    try:
        for count in scales:
            for scene in (("cube", "belts") if args.scenario == "both" else (args.scenario,)):
                spec = SceneSpec(scenario=scene, bodies=count, seed=args.seed,
                                 preset=args.preset, radius=args.radius, mass=args.mass,
                                 cube_size=args.cube_size, closing_speed=args.closing_speed,
                                 spin_speed=args.spin_speed, counter_rotate=args.counter_rotate)
                cases = []
                for repetition in range(args.repeats):
                    entry = case(spec, args, folder / f"{scene}-{count}-r{repetition}", repetition)
                    states = entry.pop("final_state_values", None)
                    if entry.get("status") == "PASS" and states is not None:
                        cases.append((entry, states))
                    reports.append(entry)
                    result["cases"].append({"scenario": scene, "bodies": count, "repetition": repetition,
                                            "status": entry["status"], "failure": entry.get("failure"),
                                            "sha256": entry.get("scene_hash"), "adapter": entry.get("adapter")})
                if len(cases) == args.repeats:
                    hashes = {entry["scene_hash"] for entry, _ in cases}
                    comparison = compare_states(cases[0][1], cases[1][1])
                    result["numerical_replays"].append(
                        {"scenario": scene, "bodies": count, "initial_hashes_equal": len(hashes) == 1,
                         "two_independent_native_runs": True, "comparison": comparison})
                    if len(hashes) != 1 or not comparison["equal"]:
                        result["cases"][-1]["status"] = "NO-GO"
                        result["cases"][-1]["failure"] = "authored hash / replay divergence"
        result["status"] = ("PASS" if len(result["cases"]) == len(scales) *
                            (2 if args.scenario == "both" else 1) * args.repeats
                            and all(c["status"] == "PASS" for c in result["cases"])
                            and all(c["comparison"]["equal"] for c in result["numerical_replays"])
                            else "NO-GO")
    except BaseException as exc:
        result["failure"] = f"{type(exc).__name__}: {exc}"
        result["exception_traceback"] = traceback.format_exc(limit=8)
    finally:
        (folder / "consolidated.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"status": result["status"], "run": str(folder),
                          "cases": result["cases"], "replay": result["numerical_replays"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
