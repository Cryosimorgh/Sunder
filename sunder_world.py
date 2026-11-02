"""Public Python headless world API for the existing native D3D12 sphere solver.

The physics state remains GPU resident across ordinary ticks. Scene edits and
explicit snapshot acquisitions incur full-state transfers. Calls are serialized.
This module does not add a CPU physics solver or promise bitwise replay.
"""
from __future__ import annotations

import ctypes as C
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
import hashlib
import itertools
import json
import math
import secrets
from pathlib import Path
import threading
import time
from typing import Optional

import numpy as np

ROOT = Path(__file__).resolve().parent
U32_MAX = (1 << 32) - 1
_WORLD_NAMESPACE = secrets.token_hex(16)
_WORLD_IDS = itertools.count(1)


class WorldError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class WorldConfig:
    capacity: int = 16
    contact_capacity: int = 128
    iterations: int = 128
    dt: float = 1 / 128
    gravity: tuple[float, float, float] = (0., 0., 0.)
    cell_size: float = 2.
    lower: tuple[float, float, float] = (-512., -512., -512.)
    upper: tuple[float, float, float] = (512., 512., 512.)
    units: str = "metre-kilogram-second"
    shader_dir: str = "evidence/p10/build"
    debug: bool = False
    deadline_ms: float = 16.

    def __post_init__(self):
        if self.units != "metre-kilogram-second":
            raise WorldError("INVALID_CONFIG", "supported units: metre-kilogram-second")
        if not (1 <= self.capacity <= 1_000_000 and
                1 <= self.contact_capacity <= 16_000_000 and
                1 <= self.iterations <= 4096):
            raise WorldError("INVALID_CONFIG", "unsupported capacity or iterations")
        numbers = [self.dt, self.cell_size, self.deadline_ms, *self.gravity,
                   *self.lower, *self.upper]
        if not all(math.isfinite(float(v)) for v in numbers):
            raise WorldError("INVALID_CONFIG", "nonfinite scalar")
        if self.dt <= 0 or self.cell_size <= 0 or self.deadline_ms <= 0:
            raise WorldError("INVALID_CONFIG", "nonpositive timestep/cell/deadline")
        if (any(lo >= hi or lo < -512 or hi > 512
                for lo, hi in zip(self.lower, self.upper))):
            raise WorldError("INVALID_CONFIG", "bounds must be within [-512,512]")
        if float(np.float32(self.dt)) <= 0 or float(np.float32(self.cell_size)) <= 0:
            raise WorldError("INVALID_CONFIG", "precision underflow")
        if any(not math.isfinite(float(np.float32(v))) for v in numbers):
            raise WorldError("INVALID_CONFIG", "binary32 overflow")


@dataclass(frozen=True)
class Body:
    position: tuple[float, float, float]
    velocity: tuple[float, float, float] = (0., 0., 0.)
    mass: float = 1.
    radius: float = .25
    restitution: float = .8
    friction: float = .3
    static: bool = False


@dataclass(frozen=True)
class Handle:
    slot: int
    generation: int
    world_id: str


@dataclass(frozen=True)
class TickResult:
    status: str
    tick: int
    epoch: int
    error_bits: int
    contacts: int
    active: int
    gpu_us: float
    cpu_us: float
    committed_bytes: int
    deadline_miss: bool
    cause: str = ""
    wall_us: float = 0.
    gpu_fixed_step_deadline_miss: bool = False
    host_fixed_step_deadline_miss: bool = False


class NativeResult(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in (
        "error", "contacts", "published", "generation", "tick",
        "max_degree", "candidates", "awake")] + [
        ("phases_us", C.c_double * 8), ("committed", C.c_uint64)]


class NativeLease(C.Structure):
    _fields_ = [("context", C.c_uint64), ("serial", C.c_uint64),
                ("buffer", C.c_uint64), ("slot", C.c_uint32),
                ("generation", C.c_uint32)]


class Backend:
    """A single owner of the pre-existing Physics3 D3D12 context."""
    def __init__(self, cfg: WorldConfig):
        directory = ROOT / cfg.shader_dir
        dll = C.WinDLL(str(directory / "physics3.dll")) if hasattr(C, "WinDLL") else C.CDLL(str(directory / "physics3.dll"))
        specs = {
            "open": ([C.c_uint32, C.c_uint32, C.c_uint32, C.c_int, C.c_char_p], C.c_void_p),
            "close": ([C.c_void_p], C.c_int),
            "seed": ([C.c_void_p, C.c_void_p, C.c_void_p, C.c_uint32], C.c_int),
            "stage": ([C.c_void_p, C.c_void_p], C.c_int),
            "drop_stage": ([C.c_void_p], C.c_int),
            "last_host_error": ([C.c_void_p], C.c_uint32),
            "resume_clock": ([C.c_void_p, C.c_uint32, C.c_float], C.c_int),
            "tick": ([C.c_void_p, C.c_float, C.c_void_p, C.c_float, C.c_uint32, C.POINTER(NativeResult)], C.c_int),
            "read": ([C.c_void_p, C.c_void_p], C.c_int),
            "acquire": ([C.c_void_p, C.POINTER(NativeLease)], C.c_int),
            "release": ([C.c_void_p, C.POINTER(NativeLease)], C.c_int),
            "adapter": ([C.c_void_p], C.c_char_p),
        }
        for name, (args, result) in specs.items():
            f = getattr(dll, "ph3_" + name)
            f.argtypes, f.restype = args, result
        self.dll = dll
        self.n = cfg.capacity
        self.ptr = dll.ph3_open(self.n, cfg.contact_capacity, cfg.iterations,
                                int(cfg.debug), str(directory).encode())
        if not self.ptr:
            raise WorldError("ALLOCATION_OR_DEVICE", "D3D12 context/admission failed")
        self.adapter = dll.ph3_adapter(self.ptr).decode(errors="replace")
        self.cfg = cfg

    def seed(self, a: np.ndarray):
        if not self.dll.ph3_seed(self.ptr, a.ctypes.data, None, 0):
            raise WorldError("DEVICE_ERROR", "initial seed failed")

    def resume_clock(self, tick: int):
        if not self.dll.ph3_resume_clock(self.ptr, tick, np.float32(self.cfg.dt)):
            raise WorldError("DEVICE_ERROR", "native clock migration failed")

    def stage(self, a: np.ndarray):
        if not self.dll.ph3_stage(self.ptr, a.ctypes.data):
            raise WorldError("DEVICE_ERROR", "candidate state staging failed")

    def discard(self):
        return bool(self.dll.ph3_drop_stage(self.ptr))

    def tick(self) -> tuple[bool, NativeResult]:
        r = NativeResult()
        g = np.asarray(self.cfg.gravity, dtype=np.float32)
        ok = bool(self.dll.ph3_tick(self.ptr, np.float32(self.cfg.dt),
                                    g.ctypes.data, np.float32(self.cfg.cell_size),
                                    0, C.byref(r)))
        return ok, r

    def host_error(self):
        return int(self.dll.ph3_last_host_error(self.ptr))

    def read(self) -> np.ndarray:
        a = np.empty((48, self.n), dtype=np.float32)
        if not self.dll.ph3_read(self.ptr, a.ctypes.data):
            raise WorldError("BACKPRESSURE_OR_DEVICE", "accepted-state readback unavailable")
        return a

    def acquire(self) -> NativeLease:
        lease = NativeLease()
        if not self.dll.ph3_acquire(self.ptr, C.byref(lease)):
            raise WorldError("BACKPRESSURE", "no available native snapshot lease")
        return lease

    def release(self, lease: NativeLease):
        if not self.dll.ph3_release(self.ptr, C.byref(lease)):
            raise WorldError("INVALID_LEASE", "expired/released native lease")

    def close(self):
        if self.ptr:
            if not self.dll.ph3_close(self.ptr):
                raise WorldError("BACKPRESSURE_OR_DEVICE", "native leases/fences not drained")
            self.ptr = None


def _ghost(a: np.ndarray, slot: int, generation: int):
    """Inert static proxies: outside the configured authoring bounds, spaced 3m."""
    a[:, slot] = 0
    a[0, slot] = 8192 + 3 * (slot % 1024)
    a[1, slot] = 8192 + 3 * ((slot // 1024) % 1024)
    a[2, slot] = 8192 + 3 * (slot // (1024 * 1024))
    a[9, slot] = 1
    a[20, slot] = .01
    a[36].view(np.uint32)[slot] = slot
    a[37].view(np.uint32)[slot] = generation


def _empty(n: int) -> np.ndarray:
    a = np.zeros((48, n), dtype=np.float32)
    # Vectorized physical inert proxies, including stable slot identity.
    k = np.arange(n, dtype=np.uint32)
    a[0] = 8192 + 3 * (k % 1024)
    a[1] = 8192 + 3 * ((k // 1024) % 1024)
    a[2] = 8192 + 3 * (k // (1024 * 1024))
    a[9] = 1
    a[20] = .01
    a[36].view(np.uint32)[:] = k
    a[37].view(np.uint32)[:] = 1
    return a


def _vector(value, length=3):
    if len(value) != length or any(not math.isfinite(float(x)) or
                                   not math.isfinite(float(np.float32(x))) for x in value):
        raise WorldError("INVALID_COMMAND", "vector must be finite")
    return np.array(value, dtype=np.float32)


def _set_body(a: np.ndarray, slot: int, generation: int, body: Body, cfg: WorldConfig):
    p, v = _vector(body.position), _vector(body.velocity)
    scalars = (body.mass, body.radius, body.restitution, body.friction)
    if (not all(math.isfinite(float(x)) and math.isfinite(float(np.float32(x))) for x in scalars)
            or body.radius <= 0 or float(np.float32(body.radius)) <= 0
            or body.radius >= cfg.cell_size / 2
            or not 0 <= body.restitution <= 1 or body.friction < 0
            or (not body.static and (body.mass <= 0 or
                float(np.float32(body.mass)) <= 0 or
                not math.isfinite(1 / float(body.mass)) or
                not math.isfinite(float(np.float32(1 / float(body.mass)))))) or body.mass < 0
            or (body.static and np.any(v))):
        raise WorldError("INVALID_COMMAND", "invalid body policy/material")
    if any(float(p[i]) - body.radius < cfg.lower[i] or
           float(p[i]) + body.radius > cfg.upper[i] for i in range(3)):
        raise WorldError("OUT_OF_BOUNDS", "body must fit authoring bounds")
    a[:, slot] = 0
    a[:3, slot], a[3:6, slot] = p, v
    a[9, slot] = 1
    a[20:23, slot] = body.radius, body.restitution, body.friction
    if not body.static:
        mass = float(body.mass)
        moment = .4 * mass * float(body.radius) ** 2
        if (not math.isfinite(moment) or moment <= 0 or
                float(np.float32(moment)) <= 0 or
                not math.isfinite(1 / moment) or
                float(np.float32(1 / moment)) <= 0 or
                not math.isfinite(float(np.float32(1 / moment)))):
            raise WorldError("INVALID_COMMAND", "inertia out of range")
        a[19, slot] = 1 / mass
        a[24:27, slot] = moment
        a[30:33, slot] = 1 / moment
    a[36].view(np.uint32)[slot] = slot
    a[37].view(np.uint32)[slot] = generation


class Snapshot:
    def __init__(self, owner: "World", lease: NativeLease, array: np.ndarray,
                 mask: np.ndarray, generations: np.ndarray, tick: int, epoch: int):
        self._owner, self._lease = owner, lease
        self._array = array
        self._mask, self._generations = mask, generations
        self.tick, self.epoch = tick, epoch
        self._closed = False
        self._array.setflags(write=False)
        self._mask.setflags(write=False)
        self._generations.setflags(write=False)

    def body(self, handle: Handle) -> dict:
        if not isinstance(handle, Handle):
            raise WorldError("STALE_HANDLE", "invalid handle type")
        i = handle.slot
        if (self._closed or handle.world_id != self._owner._world_id or i < 0 or i >= len(self._mask) or
                not self._mask[i] or self._generations[i] != handle.generation):
            raise WorldError("STALE_HANDLE", "not present in this snapshot")
        a = self._array
        inv_mass = float(a[19, i])
        return {"position": tuple(map(float, a[:3, i])),
                "velocity": tuple(map(float, a[3:6, i])),
                "orientation": tuple(map(float, a[6:10, i])),
                "angular_velocity": tuple(map(float, a[10:13, i])),
                "force": tuple(map(float, a[13:16, i])),
                "torque": tuple(map(float, a[16:19, i])),
                "mass": 1. / inv_mass if inv_mass > 0 else 0.,
                "radius": float(a[20, i]),
                "restitution": float(a[21, i]),
                "friction": float(a[22, i]),
                "static": inv_mass == 0,
                "sleep_frames": float(a[23, i])}

    def entries(self):
        if self._closed:
            raise WorldError("INVALID_LEASE", "snapshot already released")
        for i in np.flatnonzero(self._mask):
            h = Handle(int(i), int(self._generations[i]), self._owner._world_id)
            yield h, self.body(h)

    def close(self):
        if not self._closed:
            self._owner.release(self)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class World:
    def __init__(self, config: WorldConfig = WorldConfig(), backend_factory=Backend):
        self.config = config
        self._world_id = f"{_WORLD_NAMESPACE}:{next(_WORLD_IDS)}"
        self._initial_config = config
        self._lock = threading.RLock()
        self._backend_factory = backend_factory
        self._backend = backend_factory(config)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sunder-gpu")
        self._future: Optional[Future] = None
        self._busy = False
        self._closed = False
        self._closing = False
        self._faulted = None
        self.tick_id = 0
        self.epoch = 0
        self._accepted_active = np.zeros(config.capacity, dtype=bool)
        self._accepted_gen = np.ones(config.capacity, dtype=np.uint32)
        self._next_gen = np.ones(config.capacity, dtype=np.uint32)
        self._stage_state: Optional[np.ndarray] = None
        self._stage_active = None
        self._stage_gen = None
        self._free = list(range(config.capacity - 1, -1, -1))
        self._stage_free = None
        self._commands: list[dict] = []
        self._history: list[dict] = []
        self._leases: dict[int, Snapshot] = {}
        self._cache = None
        self._cache_key = None
        try:
            self._backend.seed(_empty(config.capacity))
        except BaseException:
            self._executor.shutdown(wait=True)
            self._backend.close()
            raise

    def _ready(self):
        if self._closed or self._closing:
            raise WorldError("CLOSED", "world is closing or destroyed")
        if self._busy:
            raise WorldError("BACKPRESSURE", "tick in flight")
        if self._faulted is not None:
            raise WorldError("DEVICE_ERROR", self._faulted)

    def _edit(self):
        self._ready()
        if self._stage_state is None:
            # Explicit readback only for structural/input edits, never a normal tick.
            key = (self.tick_id, self.epoch)
            # Acquire has already read a validated immutable accepted state.
            # Reuse it for safe next-boundary edits even when its native lease
            # is still held by the consumer; never mutate the snapshot copy.
            self._stage_state = (self._cache.copy() if self._cache_key == key
                                 else self._backend.read())
            self._stage_active = self._accepted_active.copy()
            self._stage_gen = self._accepted_gen.copy()
            self._stage_free = list(self._free)

    def _lookup(self, h: Handle):
        if (not isinstance(h, Handle) or h.world_id != self._world_id or
                not 0 <= h.slot < self.config.capacity or
                not self._stage_active[h.slot] or
                int(self._stage_gen[h.slot]) != h.generation):
            raise WorldError("STALE_HANDLE", "wrong slot/generation")

    def _record(self, op: str, **data):
        self._commands.append({"op": op, **data})

    def create_body(self, body: Body) -> Handle:
        with self._lock:
            self._edit()
            if not self._stage_free:
                raise WorldError("CAPACITY", "no available body slots")
            i = self._stage_free[-1]
            if int(self._next_gen[i]) == U32_MAX:
                raise WorldError("GENERATION_EXHAUSTED", str(i))
            gen = int(self._next_gen[i]) + 1
            trial = self._stage_state[:, i].copy()
            try:
                _set_body(self._stage_state, i, gen, body, self.config)
            except BaseException:
                self._stage_state[:, i] = trial
                raise
            self._stage_free.pop()
            self._next_gen[i] = gen
            self._stage_active[i] = True
            self._stage_gen[i] = gen
            h = Handle(i, gen, self._world_id)
            self._record("create", handle=asdict(h), body=asdict(body))
            return h

    def remove_body(self, h: Handle):
        with self._lock:
            self._edit()
            self._lookup(h)
            i = h.slot
            if int(self._next_gen[i]) == U32_MAX:
                raise WorldError("GENERATION_EXHAUSTED", str(i))
            gen = int(self._next_gen[i]) + 1
            _ghost(self._stage_state, i, gen)
            self._next_gen[i] = gen
            self._stage_active[i] = False
            self._stage_gen[i] = gen
            self._stage_free.append(i)
            self._record("remove", handle=asdict(h))

    def update_body(self, h: Handle, **changes):
        """Update scalar material/mass, position or velocity at the next boundary."""
        with self._lock:
            self._edit()
            self._lookup(h)
            valid = {"position", "velocity", "mass", "radius", "restitution", "friction", "static"}
            if not changes or set(changes) - valid:
                raise WorldError("INVALID_COMMAND", "unknown body field")
            a = self._stage_state
            i = h.slot
            mass = 0 if a[19, i] == 0 else 1 / float(a[19, i])
            body = Body(tuple(map(float, a[:3, i])), tuple(map(float, a[3:6, i])),
                        mass, float(a[20, i]), float(a[21, i]),
                        float(a[22, i]), a[19, i] == 0)
            body = replace(body, **changes)
            trial = a[:, i].copy()
            try:
                _set_body(a, i, h.generation, body, self.config)
            except BaseException:
                a[:, i] = trial
                raise
            # Preserve spin, orientation, forces, and sleep unless made static.
            if not body.static:
                a[6:19, i] = trial[6:19]
                a[23, i] = trial[23]
            self._record("update", handle=asdict(h), changes=changes)

    def apply_force(self, h: Handle, force):
        """Persistent world-space force in newtons; clear explicitly to stop it."""
        with self._lock:
            f = _vector(force)
            self._edit()
            self._lookup(h)
            if self._stage_state[19, h.slot] == 0:
                raise WorldError("INVALID_COMMAND", "static body")
            next_force = self._stage_state[13:16, h.slot].astype(np.float64) + f
            if not np.all(np.isfinite(next_force.astype(np.float32))):
                raise WorldError("INVALID_COMMAND", "force overflow")
            self._stage_state[13:16, h.slot] = next_force
            self._record("force", handle=asdict(h), value=list(map(float, f)))

    def clear_force(self, h: Handle):
        with self._lock:
            self._edit()
            self._lookup(h)
            self._stage_state[13:16, h.slot] = 0
            self._record("clear_force", handle=asdict(h))

    def apply_impulse(self, h: Handle, impulse):
        with self._lock:
            v = _vector(impulse)
            self._edit()
            self._lookup(h)
            inv = float(self._stage_state[19, h.slot])
            if inv <= 0:
                raise WorldError("INVALID_COMMAND", "static body")
            result = self._stage_state[3:6, h.slot].astype(np.float64) + v * inv
            if not np.all(np.isfinite(result.astype(np.float32))):
                raise WorldError("INVALID_COMMAND", "impulse overflow")
            self._stage_state[3:6, h.slot] = result
            self._stage_state[23, h.slot] = 0
            self._record("impulse", handle=asdict(h), value=list(map(float, v)))

    def cancel_pending(self):
        with self._lock:
            self._ready()
            self._clear_staging()

    def _clear_staging(self):
        self._stage_state = self._stage_active = self._stage_gen = None
        self._stage_free = None
        self._commands.clear()

    def _run_step(self, candidate, active, generations, free, commands):
        start = time.perf_counter_ns()
        thread_start = time.thread_time_ns()
        r = NativeResult()
        ok = False
        cause = ""
        discard_ok = True
        needs_discard = candidate is not None
        try:
            if candidate is not None:
                self._backend.stage(candidate)
            ok, r = self._backend.tick()
            if not ok:
                cause = "native host/device submission failure"
            elif r.error:
                cause = f"GPU rejected candidate: flags {r.error}"
            elif r.published != self.config.capacity:
                ok = False
                cause = "incomplete GPU publication"
            else:
                needs_discard = False
        except BaseException as e:
            cause = f"{type(e).__name__}: {e}"
            ok = False
        finally:
            if needs_discard:
                try:
                    discard_ok = bool(self._backend.discard())
                except BaseException as e:
                    discard_ok = False
                    cause += f"; candidate discard failed: {type(e).__name__}: {e}"
                if not discard_ok:
                    cause += "; staged source could not be safely discarded"
        wall_us = (time.perf_counter_ns() - start) / 1000
        cpu_us = (time.thread_time_ns() - thread_start) / 1000
        with self._lock:
            accepted = (ok and r.error == 0 and
                        r.published == self.config.capacity and discard_ok)
            if accepted:
                self.tick_id += 1
                if candidate is not None:
                    self._accepted_active = active
                    self._accepted_gen = generations
                    self._free = free
                    self.epoch += 1
                self._cache, self._cache_key = None, None
            if not discard_ok:
                self._faulted = cause
            if accepted:
                status = "ACCEPTED"
            elif ok and r.error and discard_ok:
                status = "REJECTED"
            elif not ok and hasattr(self._backend, "host_error") and self._backend.host_error() == 2:
                status = "BACKPRESSURE"
                cause = "all nonaccepted native snapshot slots are leased"
            else:
                status = "DEVICE_ERROR"
                self._faulted = cause or "native state may be unsafe after device failure"
            report = TickResult(status, self.tick_id, self.epoch, int(r.error),
                                int(r.contacts), int(self._accepted_active.sum()),
                                float(r.phases_us[7]), cpu_us, int(r.committed),
                                wall_us > self.config.deadline_ms * 1000, cause,
                                wall_us,
                                float(r.phases_us[7]) > self.config.dt * 1_000_000,
                                wall_us > self.config.dt * 1_000_000)
            self._history.append({"tick": self.tick_id, "commands": commands,
                                  "result": asdict(report)})
            self._clear_staging()
            self._busy = False
            return report

    def step_async(self) -> Future:
        with self._lock:
            self._ready()
            candidate = self._stage_state if any(c['op'] != 'grow' for c in self._commands) else None
            active = self._stage_active
            gen = self._stage_gen
            free = self._stage_free
            commands = list(self._commands)
            self._busy = True
            try:
                self._future = self._executor.submit(self._run_step, candidate, active,
                                                      gen, free, commands)
                return self._future
            except BaseException:
                self._busy = False
                raise

    def poll(self) -> Optional[TickResult]:
        with self._lock:
            f = self._future
        return f.result() if f is not None and f.done() else None

    def step(self) -> TickResult:
        return self.step_async().result()

    def acquire(self) -> Snapshot:
        """Explicit readback + native lease. No readback on normal simulation ticks."""
        with self._lock:
            self._ready()
            key = (self.tick_id, self.epoch)
            if self._cache_key != key:
                a = self._backend.read()
                a.setflags(write=False)
                self._cache = a
                self._cache_key = key
            lease = self._backend.acquire()
            snapshot = Snapshot(self, lease, self._cache, self._accepted_active.copy(),
                                self._accepted_gen.copy(), *key)
            self._leases[lease.serial] = snapshot
            return snapshot

    def release(self, snapshot: Snapshot):
        with self._lock:
            if snapshot._owner is not self or snapshot._closed or self._busy:
                raise WorldError("INVALID_LEASE", "foreign/released/in-flight")
            self._backend.release(snapshot._lease)
            snapshot._closed = True
            self._leases.pop(snapshot._lease.serial)

    def grow(self, capacity: int):
        """Resize at an idle boundary; IDs survive, and old context is retained on failure."""
        with self._lock:
            self._ready()
            if self._stage_state is not None or self._leases:
                raise WorldError("BACKPRESSURE", "complete edits and release leases first")
            if capacity <= self.config.capacity or capacity > 1_000_000:
                raise WorldError("INVALID_CONFIG", "growth must increase supported capacity")
            old = self._backend
            source = old.read()
            new_cfg = replace(self.config, capacity=capacity,
                              contact_capacity=max(self.config.contact_capacity, capacity))
            expanded = _empty(capacity)
            expanded[:, :self.config.capacity] = source
            # Allocate all host maps first, so allocation failure leaves the
            # old world and handles intact. The new native context is provisional.
            extra = capacity - len(self._accepted_active)
            next_active = np.pad(self._accepted_active, (0, extra))
            next_gen = np.pad(self._accepted_gen, (0, extra), constant_values=1)
            next_issue_gen = np.pad(self._next_gen, (0, extra), constant_values=1)
            next_free = list(range(capacity - 1, self.config.capacity - 1, -1)) + self._free
            fresh = self._backend_factory(new_cfg)
            try:
                fresh.seed(expanded)
                fresh.resume_clock(self.tick_id)
            except BaseException:
                try:
                    fresh.close()
                except BaseException as cleanup:
                    self._faulted = f"capacity-migration cleanup failed: {cleanup}"
                raise
            # Retire the old, fence-drained context BEFORE committing new maps.
            # If retirement fails, never reuse an uncertain native context.
            try:
                old.close()
            except BaseException as error:
                self._faulted = f"capacity-migration old-context retirement failed: {error}"
                try:
                    fresh.close()
                except BaseException as cleanup:
                    self._faulted += f"; new-context cleanup failed: {cleanup}"
                raise WorldError("DEVICE_ERROR", self._faulted) from error
            self._backend = fresh
            self.config = new_cfg
            self._accepted_active = next_active
            self._accepted_gen = next_gen
            self._next_gen = next_issue_gen
            self._free = next_free
            self.epoch += 1
            self._cache = self._cache_key = None
            self._record("grow", capacity=capacity)

    def record(self) -> dict:
        with self._lock:
            if self._busy:
                raise WorldError("BACKPRESSURE", "wait for submitted tick")
            directory = ROOT / self.config.shader_dir
            paths = [directory / "physics3.dll", ROOT / "physics3.hlsl",
                     ROOT / "physics3-schema.json", directory / "manifest.json"]
            hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in paths if p.exists()}
            return {"format": "sunder-native-numerical-v1",
                    "world_id": self._world_id,
                    "configuration": asdict(self._initial_config),
                    "provenance": {"adapter": self._backend.adapter, "sha256": hashes},
                    "steps": list(self._history),
                    "bitwise_determinism": "UNSUPPORTED"}

    def close(self):
        with self._lock:
            if self._closed:
                return
            if self._leases:
                raise WorldError("BACKPRESSURE", "release snapshots before destruction")
            self._closing = True
        self._executor.shutdown(wait=True)
        with self._lock:
            self._backend.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def replay_record(record: dict, backend_factory=Backend) -> list[tuple[TickResult, list]]:
    """Independent native run. Compares only numerical accepted snapshots."""
    if record.get("format") != "sunder-native-numerical-v1":
        raise WorldError("UNSUPPORTED_REPLAY", "expected numerical-v1 command log")
    cfg = WorldConfig(**record["configuration"])
    frames = []
    with World(cfg, backend_factory) as w:
        for event in record["steps"]:
            for command in event["commands"]:
                op = command["op"]
                if op == "grow":
                    w.grow(command["capacity"])
                elif op == "create":
                    actual = w.create_body(Body(**command["body"]))
                    if command["handle"].get("world_id") != record.get("world_id"):
                        raise WorldError("REPLAY_DIVERGENCE", "foreign create handle recorded")
                    if (actual.slot, actual.generation) != (command["handle"]["slot"], command["handle"]["generation"]):
                        raise WorldError("REPLAY_DIVERGENCE", "generated handle mismatch")
                else:
                    encoded = command["handle"]
                    if encoded.get("world_id") != record.get("world_id"):
                        raise WorldError("REPLAY_DIVERGENCE", "foreign handle recorded")
                    h = Handle(encoded["slot"], encoded["generation"], w._world_id)
                    if op == "remove":
                        w.remove_body(h)
                    elif op == "update":
                        w.update_body(h, **command["changes"])
                    elif op == "force":
                        w.apply_force(h, command["value"])
                    elif op == "clear_force":
                        w.clear_force(h)
                    elif op == "impulse":
                        w.apply_impulse(h, command["value"])
                    else:
                        raise WorldError("UNSUPPORTED_REPLAY", op)
            result = w.step()
            if result.status != event["result"]["status"]:
                raise WorldError("REPLAY_DIVERGENCE", f"tick {result.tick}: status")
            with w.acquire() as snap:
                frames.append((result, list(snap.entries())))
    return frames


def compare_replays(first, second, atol=2e-5, rtol=2e-5) -> dict:
    """Find first numerical divergence; never require equal native bytes/order."""
    if not (math.isfinite(atol) and math.isfinite(rtol) and atol >= 0 and rtol >= 0):
        raise WorldError("INVALID_CONFIG", "comparison tolerances")
    if len(first) != len(second):
        return {"equal": False, "first_divergence": "frame_count"}
    for frame, ((r0, a), (r1, b)) in enumerate(zip(first, second)):
        if (r0.status, r0.tick, r0.epoch, r0.error_bits, r0.active) != (r1.status, r1.tick, r1.epoch, r1.error_bits, r1.active):
            return {"equal": False, "first_divergence": {"frame": frame, "field": "result"}}
        if len(a) != len(b):
            return {"equal": False, "first_divergence": {"frame": frame, "field": "count"}}
        for (ha, sa), (hb, sb) in zip(a, b):
            if (ha.slot, ha.generation) != (hb.slot, hb.generation):
                return {"equal": False, "first_divergence": {"frame": frame, "field": "handle"}}
            for field in ("position", "velocity", "orientation", "angular_velocity",
                          "force", "torque", "mass", "radius", "restitution",
                          "friction", "sleep_frames", "static"):
                if not np.allclose(sa[field], sb[field], atol=atol, rtol=rtol):
                    diff = float(np.max(np.abs(np.asarray(sa[field]) - np.asarray(sb[field]))))
                    return {"equal": False, "first_divergence":
                            {"frame": frame, "tick": r0.tick, "handle": asdict(ha),
                             "field": field, "max_abs_difference": diff}}
    return {"equal": True, "first_divergence": None, "atol": atol, "rtol": rtol}
