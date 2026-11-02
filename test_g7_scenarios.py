"""Linux/Windows CPU scene-contract tests, NOT GPU qualification."""
import math
import unittest

import numpy as np

from g7_scenarios import SceneAdmissionError, SceneSpec, authored_hash, generate
from run_g7 import compare_states, topology


def check_separation(particles):
    # Bounded 3D spatial check, not N^2. Neighbor cells must include all pairs.
    cell = 1.
    grid = {}
    for particle in particles:
        b = particle.body
        p = b.position
        k = tuple(math.floor(x/cell) for x in p)
        for x in (-1,0,1):
            for y in (-1,0,1):
                for z in (-1,0,1):
                    for old in grid.get((k[0]+x,k[1]+y,k[2]+z), ()):
                        d2 = sum((a-c)**2 for a,c in zip(p,old.position))
                        assert d2 >= (b.radius + old.radius - 1e-6)**2, (
                            f"overlap {p} {old.position}")
        grid.setdefault(k, []).append(b)


class G7SceneTests(unittest.TestCase):
    def test_cube_exact_seeded_3d_nonoverlap(self):
        spec = SceneSpec("cube", 1000, preset="dense", seed=9)
        params, stream = generate(spec)
        bodies = list(stream)
        self.assertEqual(len(bodies), 1000)
        self.assertEqual(len({tuple(b.body.position) for b in bodies}), 1000)
        self.assertGreater(len({b.body.position[2] for b in bodies}), 2)
        self.assertEqual(params["geometry"], "cubic spawning volume of sphere bodies")
        check_separation(bodies)
        self.assertEqual(authored_hash(bodies), authored_hash(list(generate(spec)[1])))
        self.assertNotEqual(authored_hash(bodies),
                            authored_hash(list(generate(SceneSpec("cube",1000,seed=10,preset="dense"))[1])))

    def test_cube_never_silently_reduces_body_count(self):
        for n in (1, 16, 1024):
            params, stream = generate(SceneSpec("cube", n, preset="isolated"))
            bodies = list(stream)
            self.assertEqual(len(bodies), n)
            self.assertTrue(all(-512 < x < 512
                                for item in bodies for x in item.body.position))
        with self.assertRaises(SceneAdmissionError):
            generate(SceneSpec("cube", 1000, cube_size=1.0))
        with self.assertRaises(SceneAdmissionError):
            generate(SceneSpec("cube", 1_000_001))

    def test_belts_distinct_3d_tori_with_nonoverlap(self):
        spec = SceneSpec("belts", 1000, preset="dense", seed=31)
        params, stream = generate(spec)
        bodies = list(stream)
        self.assertEqual((sum(b.belt == 0 for b in bodies),
                          sum(b.belt == 1 for b in bodies)), (500, 500))
        self.assertGreater(params["initial_cross_belt_gap"],
                           2 * 1.03 * spec.radius)
        self.assertTrue(all(b.body.velocity[0] > 0 for b in bodies[:500]))
        self.assertTrue(all(b.body.velocity[0] < 0 for b in bodies[500:]))
        self.assertGreater(len({round(b.body.position[0], 2) for b in bodies}), 100)
        check_separation(bodies)
        self.assertEqual(authored_hash(bodies), authored_hash(list(generate(spec)[1])))
        self.assertFalse(params["self_gravity"])

    def test_contact_topology_excludes_speculative_and_checks_belt_ids(self):
        dtype = np.dtype({"names":["a","b","gap","normal_impulse"],
                          "formats":["<u4","<u4","<f8","<f8"],
                          "offsets":[0,4,80,16],"itemsize":128})
        a = np.zeros(4, dtype=dtype)
        for i, (x,y,g,imp) in enumerate(((0,1,-.1,1.), (1,2,-.1,1.),
                                         (3,4,.5,0.), (2,3,.5,2.))):
            a[i] = (x,y,g,imp)
        result, edges = topology(a, [0,0,1,1,1], 5, None)
        self.assertEqual(result["observed_edges"], 3)
        self.assertEqual(result["overlapping_contacts"], 2)
        self.assertEqual(result["cross_belt_edges"], 1)
        self.assertEqual(result["largest_island"], 4)
        self.assertNotIn((3,4), edges)
        churn, _ = topology(a, [0,0,1,1,1], 5, edges)
        self.assertEqual(churn["contact_churn_since_previous_sample"], 0)

    def test_cube_staged_static_then_dynamic_activation_host_contract(self):
        # This validates world orchestration only; FakeGPU is NOT a solver.
        from dataclasses import replace
        from test_sunder_world import FakeGPU
        from sunder_world import World, WorldConfig
        particles = list(generate(SceneSpec("cube", 8, preset="dense"))[1])
        with World(WorldConfig(capacity=8, contact_capacity=32,
                               gravity=(0., -9.8, 0.)), backend_factory=FakeGPU) as world:
            handles = []
            for start in (0, 4):
                for particle in particles[start:start+4]:
                    handles.append(world.create_body(replace(
                        particle.body, static=True, velocity=(0.,0.,0.))))
                result = world.step()
                self.assertEqual(result.status, "ACCEPTED")
                self.assertEqual(result.active, len(handles))
            with world.acquire() as snapshot:
                self.assertTrue(all(snapshot.body(h)["static"] for h in handles))
            for handle, particle in zip(handles, particles):
                world.update_body(handle, static=False, mass=particle.body.mass,
                                  velocity=particle.body.velocity)
            result = world.step()
            self.assertEqual((result.status, result.active), ("ACCEPTED", 8))
            with world.acquire() as snapshot:
                self.assertTrue(all(not snapshot.body(h)["static"] for h in handles))

    def test_controlled_perturbation_and_distribution_validation(self):
        spec = SceneSpec("belts", 128, seed=21, preset="dense",
                         radius_spread=.06, mass_spread=.2, perturbation=.04)
        params, stream = generate(spec)
        bodies = list(stream)
        self.assertEqual(params["perturbation"], .04)
        self.assertEqual(len(bodies), 128)
        self.assertEqual(authored_hash(bodies), authored_hash(list(generate(spec)[1])))
        check_separation(bodies)
        with self.assertRaises(SceneAdmissionError):
            SceneSpec("cube", 16, radius_spread=.12)
        with self.assertRaises(SceneAdmissionError):
            SceneSpec("belts", 16, perturbation=1.)
        self.assertEqual(len(list(generate(SceneSpec(
            "cube", 27, preset="dense", velocity_field="funnel"))[1])), 27)

    def test_replay_contract_not_bitwise(self):
        self.assertTrue(compare_states([(1.,2.)], [(1.,2.)])["equal"])
        mismatch = compare_states([(1.,2.)], [(1.,3.)])
        self.assertFalse(mismatch["equal"])
        self.assertEqual(mismatch["first_divergence"]["body"], 0)


if __name__ == "__main__":
    unittest.main()
