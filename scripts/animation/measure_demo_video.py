"""Run in bundled Blender: decode MP4 samples and measure blue-avatar pixel movement."""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'data' / 'demo' / 'runtime' / 'video_features.json'
EXTRACTOR = 'blue-avatar-centroid-v1'


def measure(clip):
    source = ROOT / 'data' / 'animation' / 'runtime' / clip / 'video.mp4'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x, scene.render.resolution_y = 640, 360
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.view_settings.view_transform = 'Standard'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.use_sequencer = True
    strip = scene.sequence_editor_create().strips.new_movie(clip, str(source), channel=1, frame_start=1)
    strip.transform.scale_x = strip.transform.scale_y = .5
    frames = (1, 25, 49, 72) if clip == 'R001' else (1, 25, 49, 169, 193, 217, 240)
    samples = []
    directory = ROOT / '.tools' / 'demo-measured'
    directory.mkdir(parents=True, exist_ok=True)
    for number in frames:
        if number > strip.frame_duration:
            raise ValueError('Video shorter than expected')
        scene.frame_set(number)
        path = directory / f'{clip}_{number:04d}.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path), check_existing=False)
        pixels = np.empty(640 * 360 * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        rgb = pixels.reshape(360, 640, 4)[:, :, :3]
        # shortcut: known blue jersey, fixed camera and one avatar only; reject other video domains.
        mask = ((rgb[:, :, 2] > rgb[:, :, 1] * 1.12)
                & (rgb[:, :, 1] > rgb[:, :, 0] * 1.25) & (rgb[:, :, 2] > .12))
        y, x = np.where(mask)
        if len(x) < 25 or np.ptp(x) > 90:
            raise ValueError(f'Avatar not reliably visible: {clip}/{number}')
        samples.append({'frame': number, 'time_ms': round((number - 1) * 1000 / 24, 3),
                        'centroid_x': round(float(np.mean(x)), 3), 'pixel_count': len(x),
                        'decoded_image_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        bpy.data.images.remove(image)
    a, b = samples[-3], samples[-1]
    speed = abs(b['centroid_x'] - a['centroid_x']) / ((b['time_ms'] - a['time_ms']) / 1000)
    return {'status': 'measured', 'extractor_version': EXTRACTOR,
            'video_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'late_speed_px_s': round(speed, 4), 'samples': samples}


def main():
    clips = {clip: measure(clip) for clip in ('S001', 'S002', 'R001')}
    baseline = clips['R001']['late_speed_px_s']
    if baseline < 5:
        raise ValueError('Reference movement insufficient')
    for clip, value in clips.items():
        ratio = value['late_speed_px_s'] / baseline
        if .4 < ratio < .75 or ratio > 1.5:
            raise ValueError('Measurement outside supported steady/stopping demo states')
        value.update(late_speed_ratio=round(ratio, 4), motion_state=int(ratio <= .4))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({'extractor_version': EXTRACTOR, 'clips': clips}, indent=2) + '\n', encoding='utf-8')
    print('MEASURED VIDEO PIXELS:', {k: v['late_speed_ratio'] for k, v in clips.items()}, flush=True)


if __name__ == '__main__':
    main()
