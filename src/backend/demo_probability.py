"""A specified stochastic demo world, not a trained or medical predictor."""
import json
import math
from datetime import date, datetime, timedelta

from .config import DATA, RUNTIME
from .history import sha

VERSION = 'paired-demo-bernoulli-v1'
EXTRACTOR = 'blue-avatar-centroid-v1'
# Illustrative conditional daily event rates, not estimates from medical evidence.
BASE_RATE = .004
HISTORY_RATE = .008
MOTION_RATE = .016
MOTION_PRIOR = .5


def event_probability(fatigue, motion):
    """Seven independent 24h Bernoulli intervals, constant conditional daily rate."""
    if (not isinstance(fatigue, (int, float)) or not math.isfinite(fatigue)
            or not 1 <= fatigue <= 5 or motion not in (0, 1)):
        raise ValueError('Outside the specified demo population')
    daily_rate = BASE_RATE + HISTORY_RATE * (fatigue - 1) / 4 + MOTION_RATE * motion
    return 1 - (1 - daily_rate) ** 7


def predict(history, visual):
    fatigue = history['fatigue_7d_mean']
    baseline = ((1 - MOTION_PRIOR) * event_probability(fatigue, 0)
                + MOTION_PRIOR * event_probability(fatigue, 1))
    available = visual.get('status') == 'measured'
    motion = visual.get('motion_state') if available else None
    if available:
        ratio = visual['late_speed_ratio']
        if (visual.get('extractor_version') != EXTRACTOR or not math.isfinite(ratio)
                or not (0 <= ratio <= .4 or .75 <= ratio <= 1.5)
                or motion != int(ratio <= .4)):
            raise ValueError('Unsupported or inconsistent video measurement')
    value = event_probability(fatigue, motion) if available else None
    return {'value': value, 'history_only_value': baseline, 'horizon_hours': 168,
            'model_version': VERSION, 'data_mode': 'synthetic',
            'validation_status': 'simulator_defined_not_trained_or_clinically_validated',
            'video_used': available, 'unavailable_reason': None if available else 'Video measurement unavailable',
            'target': 'New non-contact time-loss event in the next 168 hours'}


def get_paired_demo(data=DATA, runtime=RUNTIME):
    base = data / 'demo' / 'runtime'
    episodes = json.loads((base / 'episodes.json').read_text(encoding='utf-8'))
    visual = json.loads((base / 'video_features.json').read_text(encoding='utf-8'))
    if episodes['model_version'] != VERSION or visual['extractor_version'] != EXTRACTOR:
        raise ValueError('Demo artifact version mismatch; rebuild demo data')
    results = []
    digests = {}
    for episode in episodes['episodes']:
        clip = episode['current_clip_id']
        if clip not in ('S001', 'S002') or episode['reference_clip_id'] != 'R001':
            raise ValueError('Unsupported demo clip binding')
        as_of = datetime.fromisoformat(episode['as_of'])
        reference_at = datetime.fromisoformat(episode['reference_recorded_at'])
        clip_start = datetime.fromisoformat(episode['clip_start_at'])
        reference_end = datetime.fromisoformat(episode['reference_end_at'])
        if (as_of.tzinfo is None or reference_at.tzinfo is None or reference_at >= as_of
                or clip_start.tzinfo is None or reference_end.tzinfo is None
                or not reference_at < reference_end < clip_start < as_of
                or as_of - clip_start != timedelta(seconds=10)
                or episode['clip_end_at'] != episode['as_of']
                or episode['history']['coverage_days'] != 28
                or date.fromisoformat(episode['history']['cutoff']) != as_of.date() - timedelta(days=1)):
            raise ValueError('Invalid demo history/reference cutoff')
        measurement = visual['clips'][clip]
        for source_id in (clip, 'R001'):
            if source_id not in digests:
                digests[source_id] = sha(runtime / source_id / 'video.mp4')
            if digests[source_id] != visual['clips'][source_id]['video_sha256']:
                raise ValueError('Video bytes changed; rebuild measured demo features')
        # Explicit projection: no offline future events or generator internals are served.
        results.append({k: episode[k] for k in ('id', 'title', 'world_id', 'player_id', 'as_of', 'history')} | {
            'video_url': f'/api/media/{clip}/video', 'reference_video_url': '/api/media/R001/video',
            'visual': {k: measurement[k] for k in ('status', 'late_speed_ratio', 'samples', 'extractor_version')},
            'probability': predict(episode['history'], measurement),
            'target_end': (as_of + timedelta(hours=168)).isoformat()})
    return {'cases': results, 'scope': episodes['scope'], 'model_version': VERSION,
            'injury_probability': None, 'probability_status': 'not_validated',
            'limitations': [
                'Four scripted what-if worlds, two motion templates and one shared avatar reference; not an evaluation cohort.',
                'Rates are stipulated by an illustrative Bernoulli event generator, not fitted or clinically validated.',
                'Pixel tracking only supports this fixed-camera blue-avatar animation; no Foundry inference is used here.',
                'Future event draws remain offline and are not inputs to the probability calculation.']}
