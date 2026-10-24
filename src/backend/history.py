"""Only this adapter reads CSVs. Future labels never enter the runtime payload."""
import csv
import hashlib
import math
from datetime import date, timedelta
from pathlib import Path

from .config import DATA

DAILY_FIELDS = ('match_minutes', 'training_minutes', 'srpe_load', 'sleep_duration',
                'sleep_quality', 'fatigue_score', 'muscle_soreness', 'stress_level',
                'resting_hr', 'hrv_rmssd', 'total_distance', 'hsr_distance', 'sprint_distance')


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_history_summary(player_id: str, match_date: str, data: Path = DATA):
    cutoff = date.fromisoformat(match_date) - timedelta(days=1)
    start = cutoff - timedelta(days=27)
    evidence = {}
    all_past = []
    daily_path = data / 'daily_records.csv'
    injury_path = data / 'injury_history.csv'
    digests = {p.name: sha(p) for p in (daily_path, injury_path)}
    with daily_path.open(encoding='utf-8-sig', newline='') as source:
        for line, raw in enumerate(csv.DictReader(source), 2):
            if raw['player_id'] != player_id:
                continue
            day = date.fromisoformat(raw['date'])
            if day > cutoff:
                continue
            item = {key: number(raw.get(key)) for key in DAILY_FIELDS}
            item.update(player_id=player_id, date=day.isoformat())
            all_past.append(item)
            if day < start:
                continue
            eid = f'daily:{player_id}:{day.isoformat()}'
            if eid in evidence:
                raise ValueError('Duplicate player/date')
            flags = []
            if (item['hsr_distance'] is not None and item['total_distance'] is not None
                    and item['hsr_distance'] > item['total_distance']):
                flags.append('HSR exceeds total distance; distance metrics excluded')
            if any(item[key] is None for key in DAILY_FIELDS):
                flags.append('Missing/non-finite source values')
            # Distance definitions are unresolved; no distance fields enter model context.
            visible = {k: v for k, v in item.items() if k not in ('total_distance', 'hsr_distance', 'sprint_distance')}
            evidence[eid] = {'id': eid, 'kind': 'history', 'visibility': 'analyst',
                             'player_id': player_id, 'source_file': daily_path.name,
                             'source_sha256': digests[daily_path.name], 'csv_line': line,
                             'values': visible, 'quality_flags': flags}
    all_past.sort(key=lambda r: r['date'])
    metrics = []

    def metric(key, value, unit, rows, definition):
        ids = [f"daily:{player_id}:{r['date']}" for r in rows]
        metrics.append({'name': key, 'value': value, 'unit': unit, 'evidence_ids': ids,
                        'availability': 'available' if value is not None else 'missing_or_incomplete_window',
                        'window_start': rows[0]['date'] if rows else None,
                        'window_end': rows[-1]['date'] if rows else None,
                        'coverage_days': len(rows), 'definition': definition})

    recent = [r['values'] for r in evidence.values()]
    for days, offset, label in ((7, 0, '7d'), (7, 7, 'previous_7d'), (28, 0, '28d')):
        end = cutoff - timedelta(days=offset)
        begin = end - timedelta(days=days - 1)
        rows = sorted([r for r in recent if begin.isoformat() <= r['date'] <= end.isoformat()], key=lambda r: r['date'])
        for column in ('srpe_load', 'match_minutes', 'training_minutes'):
            values = [r[column] for r in rows]
            total = round(sum(values), 2) if len(rows) == days and all(v is not None for v in values) else None
            metric(f'{column}_{label}', total, 'AU' if column == 'srpe_load' else 'minutes', rows,
                   f'Sum over {days} complete calendar days; null if missing; definition v1')
        if label == '7d':
            for column, unit in (('sleep_duration', 'hours'), ('sleep_quality', '1-5 (higher better)'),
                                 ('fatigue_score', '1-5 (higher worse)'), ('muscle_soreness', '1-5 (higher worse)')):
                values = [r[column] for r in rows if r[column] is not None]
                metric(f'{column}_7d_mean', round(sum(values) / len(values), 2) if len(values) == 7 else None,
                       unit, rows, 'Mean over seven complete days; null if missing; definition v1')
    by_name = {m['name']: m for m in metrics}
    a, b = by_name['srpe_load_7d'], by_name['srpe_load_previous_7d']
    ratio = None if a['value'] is None or b['value'] in (None, 0) else round((a['value'] - b['value']) / b['value'], 3)
    metrics.append({'name': 'load_change_fraction', 'value': ratio, 'unit': 'fraction',
                    'availability': 'available' if ratio is not None else 'missing_or_zero_denominator',
                    'evidence_ids': a['evidence_ids'] + b['evidence_ids'],
                    'definition': 'Non-overlapping seven-day windows; null for missing/zero denominator; v1'})
    last14 = [r for r in recent if r['date'] >= (cutoff - timedelta(days=13)).isoformat()]
    metric('actual_appearances_14d', sum(r['match_minutes'] > 0 for r in last14)
           if len(last14) == 14 and all(r['match_minutes'] is not None for r in last14) else None,
           'appearances', last14, 'Count days match_minutes > 0, not calendar fixtures; v1')
    played = [r for r in all_past if r['match_minutes'] is not None and r['match_minutes'] > 0]
    last = played[-1] if played else None
    if last:
        eid = f"daily:{player_id}:{last['date']}"
        if eid not in evidence:
            evidence[eid] = {'id': eid, 'kind': 'history', 'visibility': 'analyst', 'player_id': player_id,
                             'source_file': daily_path.name, 'source_sha256': digests[daily_path.name],
                             'values': {k: last[k] for k in ('player_id', 'date', 'match_minutes')}}
    metrics.append({'name': 'days_since_last_appearance', 'value': (cutoff - date.fromisoformat(last['date'])).days if last else None,
                    'unit': 'days at cutoff', 'evidence_ids': [eid] if last else [], 'definition': 'As of history cutoff, v1'})
    injury_ids = []
    with injury_path.open(encoding='utf-8-sig', newline='') as source:
        for line, raw in enumerate(csv.DictReader(source), 2):
            if raw['player_id'] != player_id or date.fromisoformat(raw['injury_start_date']) > cutoff:
                continue
            eid = raw['injury_id']
            if eid in evidence:
                raise ValueError('Duplicate injury ID')
            values = {k: raw[k] for k in ('injury_start_date', 'injury_type', 'body_location', 'injury_mechanism')}
            end = date.fromisoformat(raw['injury_end_date'])
            if end <= cutoff:
                values.update(injury_end_date=end.isoformat(), days_lost=number(raw['days_lost']))
            else:
                values['status_at_cutoff'] = 'ongoing; final end date and days lost withheld'
            evidence[eid] = {'id': eid, 'kind': 'history', 'visibility': 'analyst', 'player_id': player_id,
                             'source_file': injury_path.name, 'source_sha256': digests[injury_path.name],
                             'csv_line': line, 'values': values}
            injury_ids.append(eid)
    return {'definition_version': 'history-v1', 'player_id': player_id, 'history_cutoff': cutoff.isoformat(),
            'metrics': metrics, 'past_injury_ids': injury_ids, 'evidence': evidence,
            'limitations': ['Synthetic records; no validated injury predictor.',
                            'Distance metrics excluded: HSR/Sprint definitions and source inconsistencies unresolved.',
                            'Return-to-training dates excluded due to conflicting source semantics.',
                            'ACWR, source rolling counts and z-scores are not used.']}
