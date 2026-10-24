"""Deterministic, renderer-independent motion and frame/time contract."""
import math


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def speed_at(t, motion):
    speed = motion["speed_mps"]
    if motion["profile"] == "steady":
        return speed
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
    if config["scenario_id"] not in {"S001", "S002", "S003", "R001"}:
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
    if motion["profile"] not in {"steady", "transition"}:
        raise ValueError("Unknown motion profile")
    if not (0 < motion["speed_mps"] <= 2 and 0.3 <= motion["stride_m"] <= 0.8
            and 0 < motion["foot_lift_m"] <= 0.3):
        raise ValueError("Motion parameters outside supported limits")
    if motion["profile"] == "transition":
        start, walk, stop = motion["transition_seconds"]
        if not (0 <= start < walk < stop <= config["duration_seconds"]
                and 0 < motion["walk_speed_mps"] < motion["speed_mps"]):
            raise ValueError("Invalid transition timing/speed")
