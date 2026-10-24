"""No Blender/dependencies required: python -m unittest discover -s scripts/animation."""
import copy
import json
import math
from pathlib import Path
import unittest

from motion import leg_pose, manifest, sample_frames, solve_leg, speed_at, trajectory, validate
from run_vlm import safe_file, validate_output

ROOT = Path(__file__).resolve().parents[2]


def config(clip):
    return json.loads((ROOT / "data" / "animation" / "configs" / f"{clip}.json").read_text())


class AnimationTests(unittest.TestCase):
    def test_scene_contract_and_time_mapping(self):
        for clip in ("S001", "S002", "S003", "R001"):
            c = config(clip)
            validate(c)
            m = manifest(c)
            self.assertEqual(len(m["frames"]), round(c["duration_seconds"] * c["fps"]))
            self.assertEqual(m["frames"][0]["clip_time_ms"], 0)
            self.assertEqual(m["frames"][24]["clip_time_ms"], 1000)
            self.assertEqual(m["frames"][24]["match_time_ms"], c["match_start_ms"] + 1000)
            self.assertNotIn("motion", m)
            self.assertNotIn("occlusion", m)
            self.assertEqual(len(sample_frames(m["frames"])), 10)
            window = sample_frames(m["frames"], 8, 1000, 2000)
            self.assertTrue(all(1000 <= f["clip_time_ms"] <= 2000 for f in window))

    def test_paired_scenes_have_identical_motion(self):
        a, b = config("S002"), config("S003")
        self.assertEqual(a["motion"], b["motion"])
        self.assertEqual(trajectory(a), trajectory(b))
        self.assertEqual(a["camera"], b["camera"])
        self.assertEqual(trajectory(a), trajectory(a))

    def test_slowdown_is_continuous_and_stationary_after_eight(self):
        c = config("S002")
        motion = c["motion"]
        self.assertEqual(speed_at(0, motion), speed_at(4.9, motion))
        for t in motion["transition_seconds"]:
            self.assertLess(abs(speed_at(t - 1e-5, motion) - speed_at(t + 1e-5, motion)), 1e-4)
        positions = trajectory(c)
        self.assertTrue(all(b >= a for a, b in zip(positions, positions[1:])))
        self.assertEqual(min(positions[193:]), max(positions[193:]))

    def test_feet_plant_and_ik_reconstructs_all_targets(self):
        c = config("S001")
        motion = c["motion"]
        stance_positions = []
        for i in range(1000):
            distance = i * motion["stride_m"] / 1000
            foot_x, foot_z, phase = leg_pose(distance, 0, motion)
            if phase < 0.5:
                stance_positions.append(distance + foot_x)
                self.assertEqual(foot_z, 0.095)
            hip_z = 1.005 + 0.01 * math.cos(4 * math.pi * distance / motion["stride_m"])
            hip, knee = solve_leg(foot_x, foot_z, hip_z)
            actual_x = -0.48 * (math.sin(hip) + math.sin(hip + knee))
            actual_z = hip_z - 0.48 * (math.cos(hip) + math.cos(hip + knee))
            self.assertAlmostEqual(actual_x, foot_x)
            self.assertAlmostEqual(actual_z, foot_z)
        self.assertLess(max(stance_positions) - min(stance_positions), 1e-10)

    def test_reject_invalid_config_and_empty_recheck(self):
        c = copy.deepcopy(config("S002"))
        c["motion"]["transition_seconds"] = [5, 8, 7]
        with self.assertRaises(ValueError):
            validate(c)
        with self.assertRaises(ValueError):
            sample_frames(manifest(config("S001"))["frames"], 10, 15000, 16000)

    def test_vlm_rejects_unseen_citations_and_unbounded_recheck(self):
        value = {"observations": ["The player is visible."], "evidence_frame_ids": ["S001_F0001"],
                 "view_status": "clear", "limitations": [], "review_status": "reviewed",
                 "requested_recheck": None}
        validate_output(value, {"S001_F0001"}, 10000)
        with self.assertRaises(ValueError):
            validate_output(value, {"S001_F0025"}, 10000)
        value["requested_recheck"] = {"start_ms": 0, "end_ms": 6000, "reason": "More context"}
        with self.assertRaises(ValueError):
            validate_output(value, {"S001_F0001"}, 10000)
        with self.assertRaises(ValueError):
            safe_file(ROOT / "data" / "animation" / "runtime", "../../../README.md")


if __name__ == "__main__":
    unittest.main()
