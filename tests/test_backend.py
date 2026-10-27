import asyncio
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend import app as api
from src.backend.config import DATA
from src.backend.history import get_history_summary, number
from src.backend.schemas import AnalysisRequest, MotionOutput, Recheck, validate_claims, validate_window
from src.backend.store import Store, utc
from src.backend.tools import get_frames, get_history_evidence, revision, safe_file
from src.backend.workflow import execute


def new_case(sid='S003'):
    return {'id': 'case-' + sid, 'scenario_id': sid, 'player_id': 'P001', 'mode': 'multi',
            'input_revision': revision(sid), 'created_at': utc(), 'state': 'queued',
            'calls': [], 'trace': [], 'evidence': {}, 'branch_errors': {}}


def raw(value, tool=False):
    msg = {'tool_calls': [{'function': {'name': 'request_visual_recheck', 'arguments': json.dumps(value)}}]} if tool else {'content': json.dumps(value)}
    return {'choices': [{'message': msg}]}


class FakeModel:
    """Failure/recheck injection only. Never used by the application or real evaluation."""
    def __init__(self, store, case):
        self.case = case

    async def call(self, role, instruction, content, tools=None):
        self.case['calls'].append({'role': role, 'status': 'completed', 'cache_hit': False})
        if role == 'history':
            return raw({'observations': [{'text': 'Historical training is recorded.',
                                         'evidence_ids': ['daily:P001:2026-01-24']}], 'limitations': ['Synthetic data.']})
        if role in ('motion', 'motion_recheck'):
            return raw({'observations': [{'text': 'Some body parts are hidden.', 'evidence_ids': ['S003_F0097']}]
                        if role == 'motion_recheck' else [{'text': 'A frame is visible.', 'evidence_ids': ['S003_F0001']}],
                        'view_status': 'partial', 'review_status': 'insufficient_view',
                        'requested_recheck': None, 'limitations': ['Hidden motion is unknown.']})
        if role == 'investigator':
            return raw({'start_ms': 4000, 'end_ms': 6000, 'reason': 'Inspect visibility'}, tool=True)
        if role == 'investigator_final':
            return raw({'concern': 'insufficient_evidence', 'accepted_evidence_ids': ['S003_F0001'],
                        'rejected_evidence_ids': [], 'rationale': [{'text': 'The view is limited.', 'evidence_ids': ['S003_F0001']}],
                        'limitations': ['Recheck is not independent verification.']})
        if role == 'narrative':
            # Confirm private history was removed before this model request.
            text = json.dumps(content)
            assert 'daily:' not in text and 'sleep_duration' not in text and 'injury_start' not in text
            return raw({'headline': 'A limited view', 'statements': [{'text': 'A frame is visible.', 'evidence_ids': ['S003_F0001']}],
                        'limitations': ['Some activity cannot be established.']})
        raise AssertionError(role)


class BackendTests(unittest.TestCase):
    def test_history_cutoff_windows_and_strict_json(self):
        h = get_history_summary('P001', '2026-01-25')
        serialized = json.dumps(h, allow_nan=False)
        for forbidden in ('injury_next_7d', 'exclude_from_training', 'return_to_training_date', 'load_change_pct'):
            self.assertNotIn(forbidden, serialized)
        rows = [e['values'] for e in h['evidence'].values() if e['id'].startswith('daily:')]
        self.assertTrue(all(r['date'] < '2026-01-25' for r in rows))
        self.assertEqual(len(rows), 28)
        metrics = {m['name']: m for m in h['metrics']}
        self.assertEqual(metrics['srpe_load_7d']['value'], 1574.6)
        self.assertEqual(metrics['actual_appearances_14d']['value'], 1)
        self.assertIsNone(number('inf'))
        self.assertIsNone(number('nan'))

    def test_future_poison_and_ongoing_injury_do_not_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            with (DATA / 'daily_records.csv').open(encoding='utf-8') as source:
                rows = list(csv.DictReader(source))
            for row in rows:
                if row['date'] >= '2026-01-25':
                    row['sleep_duration'] = '999999'
                    row['injury_next_7d'] = 'FUTURE_POISON'
            with (data / 'daily_records.csv').open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader(); writer.writerows(rows)
            with (DATA / 'injury_history.csv').open(encoding='utf-8') as source:
                injuries = list(csv.DictReader(source))
            injuries[0].update(injury_start_date='2026-01-23', injury_end_date='2026-02-28', days_lost='99999')
            with (data / 'injury_history.csv').open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(injuries[0]))
                writer.writeheader(); writer.writerows(injuries)
            h = get_history_summary('P001', '2026-01-25', data)
            self.assertNotIn('FUTURE_POISON', json.dumps(h))
            self.assertNotIn('999999', json.dumps(h))
            self.assertNotIn('injury_end_date', h['evidence'][injuries[0]['injury_id']]['values'])
            self.assertNotIn('days_lost', h['evidence'][injuries[0]['injury_id']]['values'])

    def test_missing_window_and_zero_denominator(self):
        early = get_history_summary('P001', '2025-08-02')
        self.assertIsNone(early['metrics'][0]['value'])
        h = get_history_summary('P001', '2026-01-10')
        fraction = next(m for m in h['metrics'] if m['name'] == 'load_change_fraction')
        self.assertIsNone(fraction['value'])
        self.assertEqual(fraction['availability'], 'missing_or_zero_denominator')

    def test_image_budget_and_time(self):
        for sid in ('S001', 'S002', 'S003'):
            content, evidence = get_frames(sid)
            self.assertEqual(sum(c['type']=='image_url' for c in content), 10)
            window = Recheck(start_ms=4000, end_ms=6000, reason='Visibility')
            content, evidence = get_frames(sid, window)
            self.assertLessEqual(sum(c['type']=='image_url' for c in content), 10)
            self.assertTrue(all(4000 <= e['clip_time_ms'] <= 6000 for e in evidence.values() if e['clip_id']==sid))
            for e in evidence.values():
                self.assertTrue(safe_file(DATA / 'animation' / 'runtime' / e['clip_id'], e['path']).is_file())

    def test_validation_rejects_unseen_frames_paths_identity_and_diagnosis(self):
        value = MotionOutput(observations=[{'text':'One leg is visible.', 'evidence_ids':['S001_F0001']}],
                             view_status='clear', review_status='no_clear_change', requested_recheck=None, limitations=[])
        with self.assertRaises(ValueError): validate_claims(value, {'S002_F0001'})
        value.observations[0].text = 'The player has a torn ligament.'
        with self.assertRaises(ValueError): validate_claims(value, {'S001_F0001'})
        with self.assertRaises(ValueError): safe_file(DATA, '../.env')
        with self.assertRaises(ValueError): validate_window(Recheck(start_ms=0,end_ms=4000,reason='Too long'),10000)
        h = get_history_summary('P001','2026-01-25')
        with self.assertRaises(ValueError): get_history_evidence(h, 'daily:P001:2026-01-24', 'P002','2026-01-24')
        with self.assertRaises(ValueError): get_history_evidence(h, 'daily:P001:2026-01-25', 'P001','2026-01-24')

    def test_store_idempotency_budget_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory)/'cases.db')
            case = new_case()
            first, created = store.create(case,'one')
            self.assertTrue(created)
            again = copy.deepcopy(case);again['id']='another'
            result, created = store.create(again,'two')
            self.assertFalse(created);self.assertEqual(result['id'],first['id'])
            with patch.dict('os.environ',{'PITCHGUARD_DAILY_CALL_LIMIT':'1'}):
                store.reserve(case['id'],'test',100)
                with self.assertRaises(ValueError): store.reserve(case['id'],'test',100)
            store.recover()
            self.assertEqual(store.get(case['id'])['state'],'failed')
            self.assertEqual(Store(store.path).get(case['id'])['id'],case['id'])

    def test_agent_framework_recheck_and_fan_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory)/'cases.db');case=new_case()
            store.create(case,'recheck')
            result = asyncio.run(execute(case,store,FakeModel))
            self.assertEqual(result['state'],'completed',result.get('error'))
            self.assertEqual(len(result['calls']),6)
            self.assertIn('recheck_request',result)
            fan=api.public_case(result,'fan')
            self.assertNotIn('history',fan)
            self.assertNotIn('decision',fan)
            self.assertTrue(all(e['kind']=='frame' for e in fan['evidence'].values()))

    def test_featured_gait_pair_inputs_and_media(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(api,'Store',lambda:Store(Path(directory)/'db')):
            with TestClient(api.app) as client:
                scenarios = client.get('/api/scenarios').json()
                self.assertEqual([s['id'] for s in scenarios[:2]], ['S006', 'S004'])
                for sid in ('S006', 'S004'):
                    self.assertEqual(AnalysisRequest(scenario_id=sid,client_request_id='test').scenario_id,sid)
                    _, evidence = get_frames(sid)
                    self.assertEqual(len(evidence),10)
                    frame = next(e for e in evidence.values() if e['clip_id']==sid)
                    self.assertEqual(client.get(frame['image_url']).status_code,200)
                    self.assertEqual(client.get(f'/api/media/{sid}/video',headers={'Range':'bytes=0-100'}).status_code,206)

    def test_api_missing_input_unknown_media_and_hosted_auth(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(api,'Store',lambda:Store(Path(directory)/'db')):
            with TestClient(api.app) as client:
                self.assertEqual(client.get('/api/health').status_code,200)
                self.assertEqual(client.get('/api/media/S002/../.env').status_code,404)
                self.assertEqual(client.get('/api/media/S005/video').status_code,404)
                self.assertEqual(client.post('/api/analyses',json={'scenario_id':'S001','player_id':'P002','client_request_id':'x'}).status_code,422)
                with patch.object(api,'LOCAL_ONLY',False),patch.object(api,'ANALYST_TOKEN','required'):
                    self.assertEqual(client.post('/api/analyses',json={'scenario_id':'S001','client_request_id':'x'}).status_code,403)
                self.assertEqual(client.get('/api/analyses/unknown').status_code,404)


if __name__ == '__main__':
    unittest.main()
