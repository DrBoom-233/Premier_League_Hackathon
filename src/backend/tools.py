import hashlib
import json
from pathlib import Path

from scripts.animation.motion import sample_frames
from scripts.animation.run_vlm import image_content, load_clip, safe_file

from .config import DATA, DEPLOYMENT, PROMPT_REVISION, ROOT, RUNTIME
from .history import get_history_summary, sha
from .schemas import Recheck, validate_window


def mapping(scenario):
    value = json.loads((DATA / 'scenario_mapping.json').read_text(encoding='utf-8'))
    if scenario not in value['scenarios']:
        raise ValueError('Unknown scenario')
    return value


def clip_context(scenario):
    meta = mapping(scenario)
    base, clip = load_clip(RUNTIME, scenario)
    refbase, ref = load_clip(RUNTIME, meta['reference_clip_id'])
    for obj, expected, clock in ((clip, scenario, meta['match_start_ms']),
                                 (ref, meta['reference_clip_id'], 4020000)):
        if (obj['player_id'] != meta['player_id'] or obj['scenario_id'] != expected
                or obj['match_start_ms'] != clock or obj['data_mode'] != 'synthetic'):
            raise ValueError('Wrong player, clip identity or match clock')
        previous = -1
        for f in obj['frames']:
            if (not f['frame_id'].startswith(expected + '_F') or f['clip_time_ms'] <= previous
                    or not 0 <= f['clip_time_ms'] < obj['duration_ms']
                    or abs(f['match_time_ms'] - clock - f['clip_time_ms']) > .01):
                raise ValueError('Invalid frame identity/time')
            previous = f['clip_time_ms']
        if len({f['frame_id'] for f in obj['frames']}) != len(obj['frames']):
            raise ValueError('Duplicate frame identity')
    return meta, base, clip, refbase, ref


def get_frames(scenario, window: Recheck | None = None):
    meta, base, clip, refbase, ref = clip_context(scenario)
    if window:
        validate_window(window, clip['duration_ms'])
        current = sample_frames(clip['frames'], 8, window.start_ms, window.end_ms)
        refs = sample_frames(ref['frames'], 2)
    else:
        current, refs = sample_frames(clip['frames'], 7), sample_frames(ref['frames'], 3)
    content = image_content(refbase, refs, 'reference') + image_content(base, current, 'current')
    evidence = {}
    for clip_id, directory, frames in ((scenario, base, current), (ref['scenario_id'], refbase, refs)):
        for frame in frames:
            evidence[frame['frame_id']] = {**frame, 'id': frame['frame_id'], 'kind': 'frame',
                 'visibility': 'public', 'clip_id': clip_id, 'player_id': meta['player_id'],
                 'source_sha256': sha(safe_file(directory, frame['path'])),
                 'image_url': f"/api/media/{clip_id}/{frame['frame_id']}"}
    return content, evidence


def get_history(scenario):
    meta = mapping(scenario)
    return get_history_summary(meta['player_id'], meta['match_date'])


def get_history_evidence(history, evidence_id, player_id, cutoff):
    if player_id != history['player_id'] or cutoff != history['history_cutoff']:
        raise ValueError('Wrong history identity or cutoff')
    if evidence_id not in history['evidence']:
        raise ValueError('Evidence is not authorized for this case')
    return history['evidence'][evidence_id]


def revision(scenario):
    """Hash actual bytes, code, model configuration and neutral mapping; no labels/configs."""
    meta, base, clip, refbase, ref = clip_context(scenario)
    digest = hashlib.sha256()
    digest.update(json.dumps(meta, sort_keys=True).encode())
    digest.update((DEPLOYMENT + PROMPT_REVISION).encode())
    import os
    for name in ('AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_VERSION'):
        digest.update(os.environ.get(name, '').encode())
    for path in [DATA / 'daily_records.csv', DATA / 'injury_history.csv',
                 *sorted((ROOT / 'src' / 'backend').glob('*.py')),
                 ROOT / 'scripts' / 'animation' / 'run_vlm.py']:
        digest.update(bytes.fromhex(sha(path)))
    for directory, obj in ((base, clip), (refbase, ref)):
        digest.update(bytes.fromhex(sha(directory / 'input_manifest.json')))
        for frame in obj['frames']:
            digest.update(bytes.fromhex(sha(safe_file(directory, frame['path']))))
    return digest.hexdigest()
