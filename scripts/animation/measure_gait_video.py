"""Blender-only pixel measurement for the fixed-camera, orange-shoe demo pair."""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR = 'orange-shoe-step-span-v1'


def measure(clip):
    source = ROOT / 'data/animation/runtime' / clip / 'video.mp4'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 640, 360
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.view_settings.view_transform = 'Standard'
    scene.render.image_settings.file_format = 'PNG'
    strip = scene.sequence_editor_create().strips.new_movie(clip, str(source), channel=1, frame_start=1)
    strip.transform.scale_x = strip.transform.scale_y = .5
    directory = ROOT / '.tools/gait-measured'
    directory.mkdir(parents=True, exist_ok=True)
    samples = []
    for number in range(121, 241):
        scene.frame_set(number)
        path = directory / f'{clip}_{number:04d}.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path), check_existing=False)
        pixels = np.empty(640 * 360 * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        rgb = pixels.reshape(360, 640, 4)[:, :, :3]
        # shortcut: orange shoes in these authored clips only; not a general gait detector.
        mask = ((rgb[:,:,0] > rgb[:,:,1]*1.35) & (rgb[:,:,1] > rgb[:,:,2]*1.4) & (rgb[:,:,0] > .25))
        y,x = np.where(mask)
        if len(x)<8 or np.ptp(x)>90:
            raise ValueError(f'Shoes not reliably visible: {clip}/{number}')
        span = float(np.percentile(x,95)-np.percentile(x,5))
        samples.append({'frame':number,'time_ms':round((number-1)*1000/24,3),'shoe_span_px':round(span,3),
                        'decoded_image_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        bpy.data.images.remove(image)
    values=np.array([s['shoe_span_px'] for s in samples])
    # Smooth compression/raster noise, then find separated maxima of foot separation.
    smooth=np.convolve(values,np.ones(3)/3,mode='valid')
    candidates=[i for i in range(3,len(smooth)-3) if smooth[i]==max(smooth[i-3:i+4])]
    peaks=[]
    for i in candidates:
        if not peaks or i-peaks[-1]>=6: peaks.append(i)
        elif smooth[i]>smooth[peaks[-1]]: peaks[-1]=i
    heights=[float(smooth[i]) for i in peaks]
    if len(heights)<4: raise ValueError('Insufficient visible steps')
    score=float(np.std(heights)/np.mean(heights))
    return {'status':'measured','extractor_version':EXTRACTOR,
            'video_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'step_span_variation':round(score,4),'peak_spans_px':[round(h,3) for h in heights],
            'samples':samples}


if __name__=='__main__':
    clips={clip:measure(clip) for clip in ('S006','S004')}
    path=ROOT/'data/demo/runtime/gait_features.json'
    path.write_text(json.dumps({'extractor_version':EXTRACTOR,'clips':clips},indent=2)+'\n',encoding='utf-8')
    print('GAIT PIXEL MEASUREMENTS:',{k:(v['step_span_variation'],v['peak_spans_px']) for k,v in clips.items()},flush=True)
