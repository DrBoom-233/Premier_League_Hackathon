"""Build four inexpensive what-if cases; no rendering, network, training or labels at runtime."""
import csv
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend.config import DATA
from src.backend.demo_probability import BASE_RATE, HISTORY_RATE, MOTION_RATE, VERSION, event_probability


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def generate(output=DATA / 'demo'):
    as_of = datetime(2026, 1, 25, 16, 10, 10, tzinfo=timezone.utc)
    profiles = {}
    for profile, fatigue in (('lower', 2), ('higher', 4)):
        rng = random.Random('paired-demo-history-' + profile)
        rows = []
        for day in range(28):
            when = as_of.date() - timedelta(days=28 - day)
            minutes = rng.randint(45, 75) if profile == 'lower' else rng.randint(80, 110)
            rpe = rng.randint(3, 5) if profile == 'lower' else rng.randint(6, 8)
            rows.append({'date': when.isoformat(), 'training_minutes': minutes, 'session_rpe': rpe,
                         'srpe_load': minutes * rpe, 'fatigue_score': fatigue,
                         'sleep_hours': round(rng.uniform(7.2, 8.5) if profile == 'lower' else rng.uniform(5.8, 7), 1)})
        profiles[profile] = rows
    episodes, future = [], []
    for index, (profile, state) in enumerate((('lower', 0), ('lower', 1), ('higher', 0), ('higher', 1)), 1):
        eid = f'DEMO{index:02d}'
        rows = profiles[profile]
        fatigue = sum(r['fatigue_score'] for r in rows[-7:]) / 7
        history = {'cutoff': rows[-1]['date'], 'coverage_days': 28,
                   'fatigue_7d_mean': fatigue,
                   'srpe_load_7d': sum(r['srpe_load'] for r in rows[-7:]),
                   'sleep_7d_mean': round(sum(r['sleep_hours'] for r in rows[-7:]) / 7, 2),
                   'profile_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()}
        episodes.append({'id': eid, 'world_id': eid, 'player_id': 'P001',
                         'title': f'{profile.capitalize()} fatigue / ' + ('slowing replay' if state else 'steady replay'),
                         'as_of': as_of.isoformat(), 'history': history,
                         'clip_start_at': (as_of - timedelta(seconds=10)).isoformat(),
                         'clip_end_at': as_of.isoformat(),
                         'current_clip_id': 'S002' if state else 'S001', 'reference_clip_id': 'R001',
                         'reference_recorded_at': (as_of - timedelta(seconds=70)).isoformat(),
                         'reference_end_at': (as_of - timedelta(seconds=67)).isoformat()})
        rng = random.Random('paired-demo-future-' + eid)
        daily_rate = BASE_RATE + HISTORY_RATE * (fatigue - 1) / 4 + MOTION_RATE * state
        events = []
        for day in range(7):
            # Event time follows the same constant-rate Bernoulli process defining the displayed probability.
            if rng.random() < daily_rate:
                at = as_of + timedelta(days=day, seconds=rng.uniform(1, 86400))
                events.append({'event_id': eid + '-EVENT', 'at': at.isoformat(),
                               'mechanism': 'Non-contact', 'days_lost': 7,
                               'return_at': (at + timedelta(days=7)).isoformat()})
                break
        future.append({'episode_id': eid, 'followup_end': (as_of + timedelta(days=7)).isoformat(),
                       'label_7d': int(bool(events)), 'events': events,
                       'generator_probability': event_probability(fatigue, state)})
    write_json(output / 'runtime' / 'episodes.json', {'model_version': VERSION,
               'scope': {'scripted_cases': 4, 'history_profiles': 2, 'days_per_profile': 28,
                         'unique_current_videos': 2, 'shared_reference_videos': 1,
                         'new_paid_calls': 0, 'new_3d_frames': 0, 'purpose': 'what_if_demo_not_training_or_calibration'},
               'episodes': episodes})
    offline = output / 'offline'
    offline.mkdir(parents=True, exist_ok=True)
    with (offline / 'history.csv').open('w', newline='', encoding='utf-8') as target:
        writer = csv.DictWriter(target, fieldnames=['history_profile', *profiles['lower'][0]])
        writer.writeheader()
        for profile, rows in profiles.items():
            writer.writerows({'history_profile': profile, **r} for r in rows)
    write_json(offline / 'future_events.json', future)
    write_json(offline / 'generation.json', {'model_version': VERSION, 'seeds': 'paired-demo-history/future + ID',
               'event_definition': 'First new non-contact time-loss event in (as_of, as_of+168h]',
               'population': 'Four stipulated what-if worlds; initially uninjured; no competing causes in this toy world',
               'event_law': {'base_daily_rate': BASE_RATE, 'fatigue_rate': HISTORY_RATE, 'slowing_rate': MOTION_RATE},
               'media': 'Reuse S001/S002/R001 templates. Shared avatar, not four independent personal baselines.',
               'qualification': 'No training, calibration, independent accuracy or medical validity claimed.'})
    return episodes


if __name__ == '__main__':
    generate()
    print('Built four paired demo worlds, 56 history rows and four offline follow-ups; no paid calls or new 3D render.')
