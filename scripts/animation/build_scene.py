"""Run inside Blender: blender -b -t 8 --python build_scene.py -- --config ..."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion import leg_pose, manifest, smooth, solve_leg, speed_at, trajectory, validate


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def material(name, rgb, roughness=0.7):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    return mat


def empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    obj.rotation_mode = "XYZ"
    return obj


def shape(name, location, scale, mat, parent=None, box=False):
    if box:
        bpy.ops.mesh.primitive_cube_add(size=2)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location, obj.scale = location, scale
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = not box
    if box:
        bevel = obj.modifiers.new("Soft edges", "BEVEL")
        bevel.width, bevel.segments = 0.08, 2
        obj.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
    return obj


def segment(name, length, radius, mat, pivot):
    return shape(name, (0, 0, -length / 2), (radius, radius, length / 2 + radius * 0.25), mat, pivot)


def create_player(mats):
    root = empty("P001_root")
    shape("Pelvis", (0, 0, 0.035), (0.17, 0.235, 0.16), mats["shorts"], root)
    torso = empty("Torso", root, (0, 0, 0.12))
    shape("Jersey", (0.015, 0, 0.24), (0.18, 0.28, 0.32), mats["jersey"], torso)
    shape("Neck", (0.03, 0, 0.58), (0.085, 0.085, 0.10), mats["skin"], torso)
    shape("Head", (0.045, 0, 0.77), (0.145, 0.14, 0.19), mats["skin"], torso)
    shape("Hair", (0.005, 0, 0.88), (0.148, 0.144, 0.10), mats["hair"], torso)
    shape("Nose", (0.18, 0, 0.77), (0.055, 0.047, 0.05), mats["skin"], torso)
    legs, arms = [], []
    for side, sign in enumerate((-1, 1)):
        hip = empty(f"Hip_{side}", root, (0, sign * 0.145, 0))
        segment(f"Shorts_{side}", 0.23, 0.125, mats["shorts"], hip)
        segment(f"Thigh_{side}", 0.48, 0.092, mats["skin"], hip)
        knee = empty(f"Knee_{side}", hip, (0, 0, -0.48))
        shape(f"Kneecap_{side}", (0, 0, 0), (0.093, 0.093, 0.093), mats["skin"], knee)
        segment(f"Calf_{side}", 0.48, 0.072, mats["socks"], knee)
        ankle = empty(f"Ankle_{side}", knee, (0, 0, -0.48))
        shape(f"Boot_{side}", (0.055, 0, -0.04), (0.16, 0.087, 0.055), mats["boots"], ankle)
        legs.append((hip, knee, ankle))
        shoulder = empty(f"Shoulder_{side}", torso, (0, sign * 0.29, 0.44))
        shoulder.rotation_euler.x = sign * 0.12
        segment(f"Sleeve_{side}", 0.15, 0.10, mats["jersey"], shoulder)
        segment(f"Upper_arm_{side}", 0.28, 0.069, mats["skin"], shoulder)
        elbow = empty(f"Elbow_{side}", shoulder, (0, 0, -0.28))
        segment(f"Forearm_{side}", 0.26, 0.058, mats["skin"], elbow)
        shape(f"Hand_{side}", (0, 0, -0.29), (0.06, 0.057, 0.08), mats["skin"], elbow)
        arms.append((shoulder, elbow))
    return root, torso, legs, arms


def create_stage(config):
    colors = {"jersey": (0.035, 0.28, 0.42), "shorts": (0.025, 0.055, 0.09),
              "socks": (0.8, 0.86, 0.88), "boots": (0.95, 0.38, 0.07),
              "skin": (0.65, 0.36, 0.22), "hair": (0.025, 0.019, 0.016),
              "grass": (0.055, 0.25, 0.115), "stripe": (0.065, 0.285, 0.135),
              "line": (0.83, 0.9, 0.85), "panel": (0.22, 0.26, 0.30)}
    mats = {key: material(key, color) for key, color in colors.items()}
    shape("Pitch", (0, 0, -0.09), (18, 12, 0.08), mats["grass"], box=True)
    for x in range(-16, 17, 4):
        shape("Mown stripe", (x, 0, -0.005), (1, 11, 0.003), mats["stripe"], box=True)
    for y in (-2.0, 5.5):
        shape("Touchline", (0, y, 0.005), (16, 0.026, 0.006), mats["line"], box=True)
    for x in (-6, 6):
        shape("Pitch marking", (x, 1.75, 0.006), (0.026, 3.75, 0.006), mats["line"], box=True)
    bpy.ops.object.camera_add(location=(0, -15, 5.6))
    camera = bpy.context.object
    camera.name = "Fixed_side_camera"
    camera.rotation_euler = (Vector((0, 0, 0.95)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = config["camera"]["ortho_scale"]
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(-3, -4, 8))
    bpy.context.object.data.energy = 1800
    bpy.context.object.data.shape = "DISK"
    bpy.context.object.data.size = 7
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 6))
    bpy.context.object.rotation_euler = (0.4, -0.5, -0.3)
    bpy.context.object.data.energy = 1.5
    world = bpy.data.worlds.new("Daylight")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.40, 0.48, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
    bpy.context.scene.world = world
    player = create_player(mats)
    panel = None
    if config.get("occlusion"):
        panel = empty("Foreground_equipment")
        shape("Equipment screen", (0, 0, 0.64), (0.78, 0.07, 0.58), mats["panel"], panel, box=True)
        for x in (-0.58, 0.58):
            shape("Equipment foot", (x, 0, 0.08), (0.08, 0.18, 0.08), mats["shorts"], panel)
    return player, panel


def animate(config, player, panel):
    root, torso, legs, arms = player
    positions = trajectory(config)
    motion = config["motion"]
    for index, x in enumerate(positions):
        frame = index + 1
        t = index / config["fps"]
        distance = x + config["path_origin_m"] + motion.get("phase_offset_m", 0)
        speed = speed_at(t, motion)
        phase = distance / motion["stride_m"]
        activity = speed / motion["speed_mps"]
        hip_z = 1.04 - 0.035 * activity + 0.01 * activity * math.cos(4 * math.pi * phase)
        root.location = (x, 0, hip_z)
        root.keyframe_insert("location", frame=frame)
        torso.rotation_euler.y = 0.11 * speed / motion["speed_mps"]
        torso.keyframe_insert("rotation_euler", frame=frame)
        for side, ((hip, knee, ankle), (shoulder, elbow)) in enumerate(zip(legs, arms)):
            foot_x, foot_z, foot_phase = leg_pose(distance, side, motion)
            foot_z = 0.095 + (foot_z - 0.095) * (0.35 + 0.65 * activity)
            # Settle any airborne foot before t=8, then retain a planted standing pose.
            if motion["profile"] == "transition":
                stop = motion["transition_seconds"][-1]
                foot_z = 0.095 + (foot_z - 0.095) * (1 - smooth((t - stop + 0.55) / 0.55))
            thigh_angle, knee_angle = solve_leg(foot_x, foot_z, hip_z)
            hip.rotation_euler.y = thigh_angle
            knee.rotation_euler.y = knee_angle
            ankle.rotation_euler.y = -thigh_angle - knee_angle
            for obj in (hip, knee, ankle):
                obj.keyframe_insert("rotation_euler", frame=frame)
            arm_amount = speed / motion["speed_mps"]
            shoulder.rotation_euler.y = 0.48 * math.cos(2 * math.pi * foot_phase) * arm_amount
            elbow.rotation_euler.y = -(0.25 + 0.9 * arm_amount)
            shoulder.keyframe_insert("rotation_euler", frame=frame)
            elbow.keyframe_insert("rotation_euler", frame=frame)
        if panel:
            start, end = config["occlusion"]["interval_seconds"]
            offset = -5 * (1 - smooth(t - start + 1)) + 5 * smooth(t - end)
            panel.location = (x + offset, -0.85, 0)
            panel.keyframe_insert("location", frame=frame)
    # Dense per-frame keys: linear interpolation prevents overshoot between samples.
    for obj in bpy.data.objects:
        if obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = "LINEAR"


def encode_video(scene, frames_dir, video_path, count):
    """Encode existing PNGs using Blender's bundled FFmpeg; no second 3D render."""
    scene.sequence_editor_clear()
    editor = scene.sequence_editor_create()
    strip = editor.strips.new_image("Rendered frames", str(frames_dir / "frame_0001.png"), 1, 1)
    for number in range(2, count + 1):
        strip.elements.append(f"frame_{number:04d}.png")
    scene.render.use_sequencer = True
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.filepath = str(video_path)
    bpy.ops.render.render(animation=True)
    scene.sequence_editor_clear()
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = "PNG"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/animation"))
    parser.add_argument("--preview", action="store_true", help="3 seconds at 640x360 in a separate directory")
    parser.add_argument("--stills", action="store_true", help="Render only 10 evenly spaced preview stills")
    parser.add_argument("--overwrite", action="store_true", help="Replace this clip's generated outputs")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    started = time.perf_counter()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    validate(config)
    if args.preview:
        config["duration_seconds"] = 3
        config["resolution"] = [640, 360]
    clip = config["scenario_id"]
    base = args.output.resolve()
    if args.preview or args.stills:
        base = base / "previews" / ("stills" if args.stills else "motion")
    runtime = base / "runtime" / clip
    frames_dir = runtime / "frames"
    if runtime.exists() and any(runtime.iterdir()) and not args.overwrite:
        parser.error(f"{runtime} already contains output; use --overwrite to regenerate")
    frames_dir.mkdir(parents=True, exist_ok=True)
    # Remove stale frames only within the explicit clip output, never source/config files.
    if args.overwrite:
        for old in frames_dir.glob("frame_*.png"):
            old.unlink()
        for name in ("input_manifest.json", "video.mp4"):
            (runtime / name).unlink(missing_ok=True)
    scenes = base / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x, scene.render.resolution_y = config["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.fps = config["fps"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    count = round(config["duration_seconds"] * config["fps"])
    scene.frame_start, scene.frame_end = 1, count
    player, panel = create_stage(config)
    animate(config, player, panel)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(scenes / f"{clip}.blend"))
    selected = list(range(1, count + 1))
    if args.stills:
        selected = [1 + round(i * (count - 1) / 9) for i in range(10)]
    frame_seconds = []
    for frame in selected:
        before = time.perf_counter()
        scene.frame_set(frame)
        scene.render.filepath = str(frames_dir / f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
        frame_seconds.append(time.perf_counter() - before)
        if len(frame_seconds) == 1:
            print(f"FIRST_FRAME_SECONDS={frame_seconds[0]:.3f}; ESTIMATE_SECONDS={frame_seconds[0] * len(selected):.1f}", flush=True)
    if not args.stills:
        encode_video(scene, frames_dir, runtime / "video.mp4", count)
        write_json(runtime / "input_manifest.json", manifest(config))
    # Production metadata belongs outside runtime, where an image-reading tool cannot see labels.
    report_dir = base / "evaluation" / "results"
    report_dir.mkdir(parents=True, exist_ok=True)
    sources = [Path(__file__), Path(__file__).with_name("motion.py")]
    write_json(report_dir / f"{clip}_generation.json", {
        "scenario_id": clip, "blender_version": bpy.app.version_string,
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        "config": config, "preview": args.preview, "stills_only": args.stills,
        "rendered_frames": len(selected), "mean_frame_seconds": sum(frame_seconds) / len(frame_seconds),
        "total_seconds": time.perf_counter() - started,
        "vlm_status": "not_run", "human_review_status": "pending"})
    print(f"COMPLETE {clip}: {len(selected)} frames in {time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
