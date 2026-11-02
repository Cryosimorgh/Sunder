"""Deterministic CPU scene authoring only; physics and contacts remain native D3D12.

P10 models spheres (not cube rigid bodies) and has no inter-body gravity.
Scenes are constructed once per repetition and never precompute contacts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import random
import struct

from sunder_world import Body


class SceneAdmissionError(ValueError):
    pass


@dataclass(frozen=True)
class SceneSpec:
    scenario: str
    bodies: int
    seed: int = 7
    preset: str = "moderate"
    radius: float = 0.40
    mass: float = 1.0
    cube_size: float | None = None
    closing_speed: float = 16.0
    spin_speed: float = 0.055
    counter_rotate: bool = True
    radius_spread: float = .03
    mass_spread: float = .10
    velocity_field: str = "inward"
    perturbation: float | None = None

    def __post_init__(self):
        if self.scenario not in ("cube", "belts"):
            raise SceneAdmissionError("scenario must be cube or belts")
        if self.preset not in ("isolated", "moderate", "dense"):
            raise SceneAdmissionError("preset must be isolated, moderate or dense")
        if not (1 <= self.bodies <= 1_000_000):
            raise SceneAdmissionError("body count outside P10 bounds")
        if not (0 < self.radius < 1 and 0 < self.mass and
                math.isfinite(self.radius) and math.isfinite(self.mass)):
            raise SceneAdmissionError("invalid material/radius")
        if not (math.isfinite(self.closing_speed) and self.closing_speed > 0 and
                math.isfinite(self.spin_speed) and self.spin_speed >= 0):
            raise SceneAdmissionError("invalid belt velocity")
        if self.cube_size is not None and (not math.isfinite(self.cube_size)
                                           or self.cube_size <= 0):
            raise SceneAdmissionError("invalid cube size")
        if not 0 <= self.radius_spread <= .08 or not 0 <= self.mass_spread <= .5:
            raise SceneAdmissionError("radius/mass distribution spread exceeds safe authored bounds")
        if self.velocity_field not in ("inward", "swirl", "funnel"):
            raise SceneAdmissionError("invalid cube velocity field")
        if self.perturbation is not None and (not math.isfinite(self.perturbation)
                                              or not 0 <= self.perturbation <= .2):
            raise SceneAdmissionError("invalid controlled belt perturbation")


@dataclass(frozen=True)
class Particle:
    body: Body
    belt: int = -1


def scene_parameters(spec: SceneSpec) -> dict:
    if spec.scenario == "cube":
        side = math.ceil(spec.bodies ** (1. / 3.))
        while side ** 3 < spec.bodies:
            side += 1
        spacing = {"isolated": 3.6, "moderate": 2.55, "dense": 2.30}[spec.preset] * spec.radius
        min_size = max(2.4 * spec.radius, (side - 1) * spacing + 2.4 * spec.radius)
        size = spec.cube_size if spec.cube_size is not None else min_size
        if size < min_size - 1e-9:
            raise SceneAdmissionError(f"cube_size {size} < safe nonoverlap minimum {min_size}")
        spacing += (size - min_size) / max(1, side - 1)
        if size / 2 + spec.radius > 512:
            raise SceneAdmissionError("cube exceeds authored [-512,512] bounds")
        return {"side": side, "pitch": spacing, "cube_size": size,
                "compression_speed": {"isolated": 0.0, "moderate": 5.0, "dense": 12.0}[spec.preset],
                "jitter_fraction": 0.01, "velocity_field": spec.velocity_field,
                "radius_spread": spec.radius_spread, "mass_spread": spec.mass_spread,
                "geometry": "cubic spawning volume of sphere bodies"}
    scale = (spec.bodies / 1000.) ** (1. / 3.)
    major = 7.0 * scale
    minor = 2.4 * scale
    center = minor + 1.8 * spec.radius
    if major + minor + spec.radius >= 512 or center + minor + spec.radius >= 512:
        raise SceneAdmissionError("torus exceeds P10 authored [-512,512] bounds")
    perturb = spec.perturbation if spec.perturbation is not None else {
        "isolated": 0., "moderate": .015, "dense": .05}[spec.preset]
    return {"major_radius": major, "minor_radius": minor,
            "centers": [[-center, 0, 0], [center, 0, 0]],
            "center_separation": 2 * center, "closing_speed": spec.closing_speed,
            "spin_speed": spec.spin_speed, "counter_rotate": spec.counter_rotate,
            "perturbation": perturb, "radius_spread": spec.radius_spread,
            "mass_spread": spec.mass_spread,
            "geometry": "two distinct toroidal 3D clouds of sphere bodies",
            "self_gravity": False, "initial_cross_belt_gap": 2 * center - 2 * minor}


def _body(spec: SceneSpec, rng: random.Random, pos, vel):
    radius = spec.radius * rng.uniform(1. - spec.radius_spread, 1. + spec.radius_spread)
    mass = spec.mass * rng.uniform(1. - spec.mass_spread, 1. + spec.mass_spread)
    return Body(position=tuple(pos), velocity=tuple(vel), radius=radius, mass=mass,
                restitution=.65, friction=.30)


def _cube(spec: SceneSpec, params: dict):
    rng = random.Random(spec.seed)
    side, pitch = params["side"], params["pitch"]
    indices = list(range(side ** 3))
    rng.shuffle(indices)
    extent = pitch * (side - 1) / 2
    for idx in indices[:spec.bodies]:
        x, y, z = idx % side, (idx // side) % side, idx // (side * side)
        pos = tuple((v * pitch - extent) + rng.uniform(-.01, .01) * pitch
                    for v in (x, y, z))
        norm = math.sqrt(sum(a * a for a in pos))
        speed = params["compression_speed"]
        vel = tuple((-speed * a / norm if norm else 0.) for a in pos)
        if spec.preset == "isolated":
            vel = (0., 0., 0.)
        elif spec.velocity_field == "swirl":
            vel = (vel[0] - .2*speed*pos[1]/max(norm, 1e-9),
                   vel[1] + .2*speed*pos[0]/max(norm, 1e-9), vel[2])
        elif spec.velocity_field == "funnel":
            vel = (vel[0], vel[1],
                   -speed * .4 * (1. if pos[2] >= 0 else -1.))
        yield Particle(_body(spec, rng, pos, vel))


class _Clearance:
    def __init__(self, cell):
        self.cell = cell
        self.grid = {}

    def insert(self, body: Body):
        p, r = body.position, body.radius
        key = tuple(math.floor(v / self.cell) for v in p)
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for c in (-1, 0, 1):
                    for other in self.grid.get((key[0]+a, key[1]+b, key[2]+c), ()):
                        distance2 = sum((x-y)**2 for x, y in zip(p, other.position))
                        if distance2 < (r + other.radius + 1e-5)**2:
                            return False
        self.grid.setdefault(key, []).append(body)
        return True


def _belts(spec: SceneSpec, params: dict):
    rng = random.Random(spec.seed)
    clearance = _Clearance(2 * (1. + spec.radius_spread) * spec.radius)
    each = ((spec.bodies + 1) // 2, spec.bodies // 2)
    for belt, target in enumerate(each):
        accepted, attempts = 0, 0
        limit = max(1000, target * 100)
        while accepted < target:
            attempts += 1
            if attempts > limit:
                raise SceneAdmissionError(
                    f"belt {belt} packing exhausted: accepted={accepted} requested={target} attempts={attempts}")
            phi = rng.uniform(0, math.tau)
            theta = rng.uniform(0, math.tau)
            rho = params["minor_radius"] * math.sqrt(rng.random())
            major_ring = params["major_radius"] + rho * math.sin(theta)
            cx = params["centers"][belt][0]
            pos = (cx + rho * math.cos(theta),
                   major_ring * math.cos(phi), major_ring * math.sin(phi))
            sign = 1. if belt == 0 else -1.
            rotation = 1. if belt == 0 or not spec.counter_rotate else -1.
            spin = spec.spin_speed * rotation
            perturb = params["perturbation"] * spec.closing_speed
            velocity = (sign * spec.closing_speed + rng.uniform(-perturb, perturb),
                        -spin * pos[2] + rng.uniform(-perturb, perturb),
                        spin * pos[1] + rng.uniform(-perturb, perturb))
            body = _body(spec, rng, pos, velocity)
            if clearance.insert(body):
                accepted += 1
                yield Particle(body, belt)


def generate(spec: SceneSpec):
    """Return (metadata, iterator). Insertion is deterministic and collision-free."""
    params = scene_parameters(spec)
    return params, _cube(spec, params) if spec.scenario == "cube" else _belts(spec, params)


def authored_hash(particles) -> str:
    h = hashlib.sha256()
    for particle in particles:
        b = particle.body
        h.update(struct.pack("<i10f", particle.belt, *b.position, *b.velocity,
                             b.radius, b.mass, b.restitution, b.friction))
    return h.hexdigest()
