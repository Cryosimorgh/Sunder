"""Sunder G7 interactive 3D capabilities viewer.

This is a visualization of the real native D3D12 world, not a CPU simulator.
Tk Canvas renders sampled accepted GPU state. It is deliberately NOT a
production-path latency benchmark: every visible frame reads back a snapshot.
Standard Python tkinter and NumPy are required; native physics3.dll must be
built using build_physics3.py on Windows x64.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import math
import os
from pathlib import Path
import sys
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

from g7_scenarios import SceneSpec, generate
from sunder_world import World, WorldConfig

COLORS = {"cube": "#60cbff", 0: "#60a5fa", 1: "#fb923c"}
BACKGROUND = "#091221"


def camera_project(p, width, height, extent, azimuth, elevation, zoom=1.0):
    """Perspective projection and sortable camera depth, pure for CPU tests."""
    ca, sa = math.cos(azimuth), math.sin(azimuth)
    ce, se = math.cos(elevation), math.sin(elevation)
    camera = (ce * ca, ce * sa, se)
    right = (-sa, ca, 0.)
    up = (-se * ca, -se * sa, ce)
    depth = sum(a * b for a, b in zip(p, camera))
    distance = max(8., extent * 3.8)
    denominator = max(0.5, distance - depth)
    scale = min(width, height) * .77 * zoom / max(2., 2 * extent)
    scale *= distance / denominator
    x = width / 2 + sum(a * b for a, b in zip(p, right)) * scale
    y = height / 2 - sum(a * b for a, b in zip(p, up)) * scale
    return x, y, depth, scale


def scene_extents(spec, params):
    if spec.scenario == "cube":
        h = params["cube_size"] / 2
        return max(2., h + spec.radius * 2)
    return max(params["major_radius"] + params["minor_radius"] + 1.0,
               params["center_separation"] / 2 + params["minor_radius"] + 1.0)


class NativeVisualWorld:
    """Worker-thread owner; only physics world provides motion."""
    def __init__(self):
        self.world = None
        self.particles = []
        self.handles = []
        self.id_to_belt = {}
        self.cursor = 0
        self.fill_tick = None
        self.last_points = []
        self.stopped = False
        self.spec = None
        self.params = {}
        self.batch = 0

    def close(self):
        if self.world is not None:
            self.world.close()
            self.world = None

    def reset(self, scenario, preset, bodies, batch, seed):
        self.close()
        self.spec = SceneSpec(scenario, bodies, seed=seed, preset=preset)
        self.params, stream = generate(self.spec)
        self.particles = list(stream)
        if len(self.particles) != bodies:
            raise RuntimeError("scene generator did not produce all requested bodies")
        self.batch = batch
        self.handles = []
        self.id_to_belt = {}
        self.cursor = 0
        self.fill_tick = None
        self.last_points = []
        self.stopped = False
        contact_cap = min(16_000_000, max(128, bodies * 24))
        self.world = World(WorldConfig(capacity=bodies, contact_capacity=contact_cap,
                                      iterations=128, dt=1 / 128, gravity=(0., 0., 0.)))
        return {"description": "Native D3D12 world initialized",
                "scene": scenario, "preset": preset, "capacity": bodies,
                "params": self.params,
                "adapter": self.world._backend.adapter,
                "extent": scene_extents(self.spec, self.params),
                "points": [], "tick": 0, "active": 0,
                "status": "READY", "contacts": 0, "gpu_us": 0., "wall_us": 0.,
                "candidates": 0, "max_degree": 0, "committed_bytes": 0,
                "readback_ms": 0., "stage_us": 0., "post_full": 0}

    def advance(self, ticks=1):
        if self.world is None:
            raise RuntimeError("native world is not initialized")
        if self.stopped:
            raise RuntimeError("native simulation stopped after rejection")
        result = None
        for _ in range(ticks):
            scene = self.spec.scenario
            if scene == "belts":
                count = self.spec.bodies - self.cursor
            else:
                count = min(self.batch, self.spec.bodies - self.cursor)
            for particle in self.particles[self.cursor:self.cursor + count]:
                body = particle.body
                if scene == "cube":
                    body = replace(body, static=True, velocity=(0., 0., 0.))
                handle = self.world.create_body(body)
                self.handles.append(handle)
                self.id_to_belt[handle.slot] = particle.belt
            self.cursor += count
            if scene == "cube" and self.fill_tick is not None and (
                    self.world.tick_id == self.fill_tick):
                for handle, particle in zip(self.handles, self.particles):
                    self.world.update_body(handle, static=False,
                                           mass=particle.body.mass,
                                           velocity=particle.body.velocity)
            result = self.world.step()
            if result.status != "ACCEPTED":
                self.stopped = True
                break
            if self.cursor == self.spec.bodies and self.fill_tick is None:
                self.fill_tick = result.tick
        if result is None:
            raise RuntimeError("no native tick executed")
        start = time.perf_counter_ns()
        points = self.last_points
        if result.status == "ACCEPTED":
            with self.world.acquire() as snap:
                points = [(body["position"], body["radius"],
                           self.id_to_belt[handle.slot], body["static"])
                          for handle, body in snap.entries()]
            self.last_points = points
        readback_ms = (time.perf_counter_ns() - start) / 1e6
        return {
            "scene": self.spec.scenario, "preset": self.spec.preset,
            "capacity": self.spec.bodies, "params": self.params,
            "adapter": self.world._backend.adapter,
            "extent": scene_extents(self.spec, self.params),
            "points": points, "tick": result.tick, "active": result.active,
            "status": result.status, "cause": result.cause,
            "error_bits": result.error_bits, "contacts": result.contacts,
            "gpu_us": result.gpu_us, "wall_us": result.wall_us,
            "candidates": result.gpu_candidates,
            "max_degree": result.gpu_max_degree,
            "committed_bytes": result.committed_bytes,
            "stage_us": result.candidate_stage_us,
            "readback_ms": readback_ms,
            "post_full": max(0, result.tick - (self.fill_tick or result.tick)),
            "spawned": self.cursor, "fill_tick": self.fill_tick}


class G7Window:
    def __init__(self, root, args):
        self.root = root
        self.root.title("Sunder G7 — Live Native 3D Capabilities")
        self.root.geometry("1320x820")
        self.root.minsize(940, 580)
        self.root.configure(bg=BACKGROUND)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="g7-visual")
        self.bridge = NativeVisualWorld()
        self.pending = None
        self.pending_action = None
        self.running = False
        self.start_requested = False
        self.reset_requested = False
        self.last = None
        self.camera_az = math.radians(40)
        self.camera_el = math.radians(26)
        self.camera_zoom = 1.0
        self.drag = None
        self.max_draw = 2200
        self._last_redraw = 0.
        self.scenario = tk.StringVar(value=args.scenario)
        self.preset = tk.StringVar(value=args.preset)
        self.body_count = tk.IntVar(value=args.bodies)
        self.batch = tk.IntVar(value=args.spawn_batch)
        self.seed = tk.IntVar(value=args.seed)
        self.ticks_per_frame = tk.IntVar(value=1)
        self.stat = tk.StringVar(value="Loading native D3D12 world...")
        self.message = tk.StringVar(value="The display samples real accepted GPU state.")
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.reset()
        self.root.after(30, self.poll)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=8)
        outer.pack(fill="both", expand=True)
        tools = ttk.Frame(outer, padding=(3, 2, 3, 10))
        tools.pack(fill="x")
        for title, var, options in (
                ("Scene", self.scenario, ("cube", "belts")),
                ("Density", self.preset, ("isolated", "moderate", "dense"))):
            ttk.Label(tools, text=title).pack(side="left", padx=(7, 3))
            ttk.Combobox(tools, textvariable=var, values=options,
                         state="readonly", width=11).pack(side="left")
        for title, var, limit in (
                ("Bodies", self.body_count, 3000),
                ("Batch", self.batch, 3000),
                ("Seed", self.seed, 999999)):
            ttk.Label(tools, text=title).pack(side="left", padx=(12, 3))
            tk.Spinbox(tools, from_=1, to=limit, textvariable=var,
                       width=7).pack(side="left")
        ttk.Button(tools, text="Load / Reset", command=self.reset).pack(side="left", padx=10)
        self.play_button = ttk.Button(tools, text="Play", command=self.toggle)
        self.play_button.pack(side="left")
        ttk.Label(tools, text="Ticks / frame").pack(side="left", padx=(10, 3))
        tk.Spinbox(tools, from_=1, to=16, width=4,
                   textvariable=self.ticks_per_frame).pack(side="left")
        ttk.Button(tools, text="Reset camera", command=self.reset_camera).pack(
            side="left", padx=(10, 2))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, bg=BACKGROUND, borderwidth=0,
                                highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        info = ttk.Frame(body, padding=(14, 12))
        info.pack(side="right", fill="y")
        ttk.Label(info, text="LIVE NATIVE DEBUG",
                  font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(4, 10))
        ttk.Label(info, textvariable=self.stat, justify="left",
                  font=("Consolas", 10)).pack(anchor="nw")
        ttk.Separator(info).pack(fill="x", pady=14)
        ttk.Label(info, text="GPU physics: D3D12\n"
                  "Display: Tk Canvas + explicit GPU readback\n"
                  "Not a production-path benchmark",
                  justify="left").pack(anchor="w")
        ttk.Label(outer, textvariable=self.message, anchor="w").pack(fill="x", pady=(8, 0))
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        self.canvas.bind("<MouseWheel>", self.zoom_mouse)
        self.canvas.bind("<Button-4>", lambda _event: self.zoom(1.1))
        self.canvas.bind("<Button-5>", lambda _event: self.zoom(1 / 1.1))
        self.canvas.bind("<Configure>", lambda _event: self.draw())

    def _settings(self):
        bodies = int(self.body_count.get())
        batch = int(self.batch.get())
        if not 1 <= bodies <= 3000 or not 1 <= batch <= 3000:
            raise ValueError("GUI body and batch counts must be in [1,3000]")
        return self.scenario.get(), self.preset.get(), bodies, batch, int(self.seed.get())

    def reset(self):
        self.running = False
        self.play_button.configure(text="Play")
        if self.pending is not None:
            self.reset_requested = True
            return
        try:
            settings = self._settings()
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Invalid scene settings", str(exc))
            return
        self.last = None
        self.message.set("Creating the native D3D12 scene...")
        self.pending = self.pool.submit(self.bridge.reset, *settings)
        self.pending_action = "reset"
        self.draw()

    def toggle(self):
        if self.running:
            self.running = False
            self.play_button.configure(text="Play")
            self.message.set("Paused. Drag to orbit; scroll to zoom.")
        else:
            self.running = True
            self.play_button.configure(text="Pause")
            if self.pending is None and self.last and self.last.get("status") != "REJECTED":
                self.step()

    def step(self):
        if self.pending is not None or not self.running:
            return
        try:
            ticks = max(1, min(16, int(self.ticks_per_frame.get())))
        except (tk.TclError, ValueError):
            ticks = 1
        self.pending = self.pool.submit(self.bridge.advance, ticks)
        self.pending_action = "step"

    def poll(self):
        if self.pending is not None and self.pending.done():
            action = self.pending_action
            future = self.pending
            self.pending = None
            self.pending_action = None
            try:
                self.last = future.result()
            except BaseException as exc:
                self.running = False
                self.play_button.configure(text="Play")
                self.message.set("ERROR: " + str(exc))
                self.stat.set(traceback.format_exc(limit=5)[-1100:])
            else:
                self.draw()
                if action == "reset":
                    self.message.set("Loaded native D3D12 adapter: " +
                                     str(self.last.get("adapter", "")) +
                                     ". Press Play to simulate.")
                elif self.last["status"] != "ACCEPTED":
                    self.running = False
                    self.play_button.configure(text="Play")
                    self.message.set("NATIVE TICK REJECTED: " +
                                     self.last.get("cause", "unknown failure"))
            if self.reset_requested:
                self.reset_requested = False
                self.reset()
            elif self.running:
                self.step()
        self.root.after(30, self.poll)

    def reset_camera(self):
        self.camera_az = math.radians(40)
        self.camera_el = math.radians(26)
        self.camera_zoom = 1.0
        self.draw()

    def drag_start(self, event):
        self.drag = (event.x, event.y)

    def drag_move(self, event):
        if self.drag is None:
            return
        x, y = self.drag
        self.camera_az += (event.x - x) * .006
        self.camera_el = max(-1.45, min(1.45, self.camera_el +
                                          (event.y - y) * .006))
        self.drag = (event.x, event.y)
        self.draw()

    def zoom(self, multiplier):
        self.camera_zoom = max(.18, min(8., self.camera_zoom * multiplier))
        self.draw()

    def zoom_mouse(self, event):
        self.zoom(1.1 if event.delta > 0 else 1 / 1.1)

    def draw(self):
        if not hasattr(self, "canvas"):
            return
        canvas = self.canvas
        canvas.delete("all")
        width, height = max(canvas.winfo_width(), 100), max(canvas.winfo_height(), 100)
        if not self.last:
            canvas.create_text(width / 2, height / 2,
                               text="SUNDER G7\nInitializing native physics...",
                               font=("Segoe UI", 20), fill="#cbd5e1",
                               justify="center")
            return
        data = self.last
        extent = data["extent"]
        def project(pos):
            return camera_project(pos, width, height, extent,
                                  self.camera_az, self.camera_el, self.camera_zoom)

        if data["scene"] == "cube":
            h = data["params"]["cube_size"] / 2
            corners = [(x * h, y * h, z * h)
                       for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
            for i, a in enumerate(corners):
                for j, b in enumerate(corners[i+1:], i+1):
                    if sum(a[k] != b[k] for k in range(3)) == 1:
                        x1, y1, _, _ = project(a)
                        x2, y2, _, _ = project(b)
                        canvas.create_line(x1, y1, x2, y2,
                                           fill="#3b627e", width=1)
        else:
            for belt in (0, 1):
                cx = data["params"]["centers"][belt][0]
                radius = data["params"]["major_radius"]
                coords = []
                for j in range(97):
                    angle = 2 * math.pi * j / 96
                    x, y, _, _ = project((cx, radius * math.cos(angle),
                                         radius * math.sin(angle)))
                    coords.extend((x, y))
                canvas.create_line(*coords, fill="#1d4e76" if belt == 0 else
                                   "#704625", width=1)

        points = data["points"]
        stride = max(1, math.ceil(len(points) / self.max_draw))
        spheres = []
        for p, radius, belt, frozen in points[::stride]:
            px, py, depth, scale = project(p)
            r = max(1., min(45., radius * scale))
            if not (-r < px < width+r and -r < py < height+r):
                continue
            spheres.append((depth, px, py, r, belt, frozen))
        spheres.sort(key=lambda item: item[0])
        for depth, px, py, radius, belt, frozen in spheres:
            color = (COLORS["cube"] if belt == -1 else COLORS[belt])
            outline = "#e2e8f0" if frozen else ""
            canvas.create_oval(px-radius, py-radius, px+radius, py+radius,
                               fill=color, outline=outline, width=1)
            if radius >= 4:
                canvas.create_oval(px-radius*.45, py-radius*.55,
                                   px-radius*.12, py-radius*.23,
                                   fill="#d6efff" if belt != 1 else "#ffdfae",
                                   outline="")
        canvas.create_text(16, 14, anchor="nw",
                           text=("CUBE — 3D VOLUME SPAWNING" if data["scene"] == "cube"
                                 else "ASTEROIDS — CONVERGING 3D TOROIDAL BELTS"),
                           fill="#e2e8f0", font=("Segoe UI", 13, "bold"))
        canvas.create_text(16, 40, anchor="nw",
                           text=f"Visible: {len(spheres):,} / active: {data['active']:,}  "
                                "   •  Drag to orbit  •  Wheel to zoom",
                           fill="#a3b3c8", font=("Consolas", 10))
        stats = (
            f"Status        {data['status']}\n"
            f"Adapter       {str(data.get('adapter',''))[:27]}\n"
            f"Scene         {data['scene']} / {data['preset']}\n"
            f"Tick          {data['tick']:,}\n"
            f"Active        {data['active']:,} / {data['capacity']:,}\n"
            f"Fill tick     {data.get('fill_tick') or '-'}\n"
            f"After full    {data.get('post_full', 0):,} ticks\n"
            f"Contacts      {data['contacts']:,}\n"
            f"Candidates    {data['candidates']:,}\n"
            f"Max degree    {data['max_degree']:,}\n"
            f"GPU step      {data['gpu_us']/1000:.3f} ms\n"
            f"Host step     {data['wall_us']/1000:.3f} ms\n"
            f"Staging       {data['stage_us']/1000:.3f} ms\n"
            f"Readback      {data['readback_ms']:.3f} ms\n"
            f"GPU committed {data['committed_bytes']/1048576:.1f} MiB\n"
            f"Error bits    {data.get('error_bits',0)}\n"
            f"Drawn spheres {len(spheres):,}"
        )
        self.stat.set(stats)

    def close(self):
        self.running = False
        try:
            self.pool.submit(self.bridge.close)
            self.pool.shutdown(wait=False)
        except RuntimeError:
            pass
        self.root.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("cube", "belts"), default="cube")
    parser.add_argument("--preset", choices=("isolated", "moderate", "dense"),
                        default="dense")
    parser.add_argument("--bodies", type=int, default=512)
    parser.add_argument("--spawn-batch", type=int, default=32)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    if os.name != "nt":
        parser.error("live D3D12 native physics requires Windows x64")
    root = tk.Tk()
    G7Window(root, args)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
