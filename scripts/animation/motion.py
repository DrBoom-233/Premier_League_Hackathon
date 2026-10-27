"""Deterministic, renderer-independent motion and frame/time contract."""
import math
from bisect import bisect_right

SCENARIO_IDS = ("S001", "S002", "S003", "S004", "S006")
CLIP_IDS = (*SCENARIO_IDS, "R001")


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def speed_at(t, motion):
    speed = motion["speed_mps"]
    if motion["profile"] == "steady":
        return speed
    if motion["profile"] == "slow_walk":
        start, walk = motion["transition_seconds"]
        return speed + (motion["walk_speed_mps"] - speed) * smooth((t - start) / (walk - start))
    start, walk, stop = motion["transition_seconds"]
    walking = motion["walk_speed_mps"]
    if t < start:
        return speed
    if t < walk:
        return speed + (walking - speed) * smooth((t - start) / (walk - start))
    return walking * (1 - smooth((t - walk) / (stop - walk)))


def trajectory(config):
    """Integrate velocity once; paired scenarios have identical root motion."""
    fps = config["fps"]
    count = round(config["duration_seconds"] * fps)
    positions = [0.0]
    for frame in range(1, count):
        a, b = (frame - 1) / fps, frame / fps
        positions.append(positions[-1] + (speed_at(a, config["motion"]) +
                                          speed_at(b, config["motion"])) / (2 * fps))
    # Shared start position: steady and changing clips use the same camera/path origin.
    return [x - config["path_origin_m"] for x in positions]


def leg_pose(distance, side, motion):
    """World-planted stance, eased swing and analytical two-segment IK.

    shortcut: stylized fixed stride, not a biomechanical gait; replace for natural walking.
    Phase follows distance, so slowing the root also slows the limbs.
    """
    stride = motion["stride_m"]
    phase = distance / stride + side * 0.5
    cycle = math.floor(phase)
    phase -= cycle
    plant = (cycle - side * 0.5) * stride + stride * 0.25
    if phase < 0.5:
        foot_x, lift = plant, 0.0
    else:
        swing = (phase - 0.5) * 2
        foot_x = plant + stride * smooth(swing)
        lift = motion["foot_lift_m"] * math.sin(math.pi * swing) ** 2
    return foot_x - distance, 0.095 + lift, phase


def solve_leg(foot_x, foot_z, hip_z, length=0.48):
    dz = foot_z - hip_z
    reach = math.hypot(foot_x, dz)
    if not 0.01 < reach < 2 * length:
        raise ValueError(f"Unreachable foot target: {reach:.4f}m")
    height = math.sqrt(length * length - reach * reach / 4)
    knee_x = foot_x / 2 - dz / reach * height
    knee_z = dz / 2 + foot_x / reach * height
    thigh = math.atan2(-knee_x, -knee_z)
    shin = math.atan2(-(foot_x - knee_x), -(dz - knee_z))
    return thigh, shin - thigh


def gait_track(config):
    """Plan touchdown/liftoff events; keep each stance anchor fixed in world space.

    shortcut: authored asymmetry for a fictional limp, not a medically derived gait.
    Freeze step parameters at planning time so the transition cannot slide planted feet.
    """
    motion = config["motion"]
    stride, fps = motion["stride_m"], config["fps"]
    distances = [x + config["path_origin_m"] for x in trajectory(config)]
    asymmetry = motion.get("asymmetry")

    def amount(t):
        if not asymmetry:
            return 0.0
        start, end = asymmetry["transition_seconds"]
        return asymmetry["strength"] * smooth((t - start) / (end - start))

    def time_at(distance):
        index = max(0, min(len(distances) - 2, bisect_right(distances, distance) - 1))
        a, b = distances[index:index + 2]
        return (index + (distance - a) / (b - a)) / fps

    events = [[], []]
    for cycle in range(-2, math.ceil(distances[-1] / stride) + 3):
        start = cycle * stride
        strength = amount(time_at(start - stride * 0.5))
        # Near-camera leg takes a short step and unloads earlier; the other covers it.
        for side in (0, 1):
            touchdown = start + (0 if side == 0 else 0.5 - 0.15 * strength) * stride
            duty = 0.5 + (-0.10 if side == 0 else 0.25) * strength
            forward = stride * 0.25 + ((0.01 if side == 0 else 0.28) - stride * 0.25) * strength
            events[side].append((touchdown, touchdown + duty * stride, touchdown + forward, strength))

    track = []
    for index, distance in enumerate(distances):
        t = index / fps
        strength, activity = amount(t), speed_at(t, motion) / motion["speed_mps"]
        cycle_phase = (distance / stride) % 1
        dip = math.sin(math.pi * min(cycle_phase / 0.40, 1)) ** 2
        hip_z = (1.04 - 0.035 * activity + 0.01 * activity * math.cos(4 * math.pi * cycle_phase)
                 - strength * (0.028 + 0.028 * dip))
        feet = []
        for side in (0, 1):
            steps = events[side]
            step = bisect_right([event[0] for event in steps], distance) - 1
            touchdown, liftoff, plant, step_strength = steps[step]
            next_touchdown, _, next_plant, _ = steps[step + 1]
            if distance <= liftoff:
                foot_x, lift = plant, 0.0
                phase = 0.5 * (distance - touchdown) / (liftoff - touchdown)
            else:
                swing = (distance - liftoff) / (next_touchdown - liftoff)
                foot_x = plant + (next_plant - plant) * smooth(swing)
                lift = (motion["foot_lift_m"] * (0.35 + 0.65 * activity)
                        * (1 - (0.65 if side == 0 else 0.15) * step_strength)
                        * math.sin(math.pi * swing) ** 2)
                phase = 0.5 + swing * 0.5
            feet.append((foot_x - distance, 0.095 + lift, phase))
        track.append({"hip_z": hip_z, "torso_roll": 0.065 * strength * math.sin(2 * math.pi * cycle_phase),
                      "feet": feet})
    return track


def manifest(config, frame_numbers=None):
    count = round(config["duration_seconds"] * config["fps"])
    frame_numbers = frame_numbers if frame_numbers is not None else range(1, count + 1)
    clip = config["scenario_id"]
    frames = []
    for number in frame_numbers:
        time_ms = round((number - 1) * 1000 / config["fps"], 3)
        frames.append({"frame_id": f"{clip}_F{number:04d}",
                       "path": f"frames/frame_{number:04d}.png",
                       "clip_time_ms": time_ms,
                       "match_time_ms": config["match_start_ms"] + time_ms})
    return {"schema_version": "1", "scenario_id": clip, "player_id": "P001",
            "data_mode": "synthetic", "duration_ms": round(count * 1000 / config["fps"]),
            "fps": config["fps"], "render_frame_start": 1,
            "match_start_ms": config["match_start_ms"], "video_path": "video.mp4",
            "reference_clip_id": config.get("reference_clip_id"), "frames": frames}


def sample_frames(frames, count=10, start_ms=None, end_ms=None):
    candidates = [f for f in frames if (start_ms is None or f["clip_time_ms"] >= start_ms)
                  and (end_ms is None or f["clip_time_ms"] <= end_ms)]
    if not candidates:
        raise ValueError("No frames in requested interval")
    count = min(count, len(candidates))
    if count < 2:
        return candidates[:1]
    return [candidates[round(i * (len(candidates) - 1) / (count - 1))] for i in range(count)]


def validate(config):
    if config["scenario_id"] not in CLIP_IDS:
        raise ValueError("Unknown neutral scenario ID")
    if not 1 <= config["duration_seconds"] <= 30 or not 1 <= config["fps"] <= 60:
        raise ValueError("Duration/fps outside supported limits")
    if abs(config["duration_seconds"] * config["fps"] -
           round(config["duration_seconds"] * config["fps"])) > 1e-6:
        raise ValueError("Duration must contain an integer number of frames")
    width, height = config["resolution"]
    if not (64 <= width <= 1920 and 64 <= height <= 1080 and width % 2 == height % 2 == 0):
        raise ValueError("Use even dimensions between 64x64 and 1920x1080")
    motion = config["motion"]
    if motion["profile"] not in {"steady", "transition", "slow_walk"}:
        raise ValueError("Unknown motion profile")
    if not (0 < motion["speed_mps"] <= 2 and 0.3 <= motion["stride_m"] <= 0.8
            and 0 < motion["foot_lift_m"] <= 0.3):
        raise ValueError("Motion parameters outside supported limits")
    if motion["profile"] == "transition":
        start, walk, stop = motion["transition_seconds"]
        if not (0 <= start < walk < stop <= config["duration_seconds"]
                and 0 < motion["walk_speed_mps"] < motion["speed_mps"]):
            raise ValueError("Invalid transition timing/speed")
    if motion["profile"] == "slow_walk":
        start, walk = motion["transition_seconds"]
        if not (0 <= start < walk <= config["duration_seconds"]
                and 0 < motion["walk_speed_mps"] < motion["speed_mps"]):
            raise ValueError("Invalid walking transition")
    if "asymmetry" in motion:
        start, end = motion["asymmetry"]["transition_seconds"]
        if (motion["profile"] != "slow_walk" or not 0 <= start < end <= config["duration_seconds"]
                or not 0 <= motion["asymmetry"]["strength"] <= 1):
            raise ValueError("Invalid asymmetry transition/strength")
