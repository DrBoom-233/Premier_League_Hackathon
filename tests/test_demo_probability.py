import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts.prepare_multimodal_demo import generate
from src.backend import app as api
from src.backend.config import DATA, RUNTIME
from src.backend.demo_probability import EXTRACTOR, event_probability, get_paired_demo, predict
from src.backend.history import sha
from src.backend.store import Store


class PairedDemoTests(unittest.TestCase):
    def measurement(self, motion):
        return {'status': 'measured', 'extractor_version': EXTRACTOR,
                'motion_state': motion, 'late_speed_ratio': 0.001 if motion else 1.0}

    def test_video_changes_joint_probability_with_identical_history(self):
        history = {'fatigue_7d_mean': 2}
        steady, slowing = [predict(history, self.measurement(state)) for state in (0, 1)]
        self.assertEqual(steady['history_only_value'], slowing['history_only_value'])
        self.assertLess(steady['value'], steady['history_only_value'])
        self.assertGreater(slowing['value'], slowing['history_only_value'])
        self.assertEqual(steady['value'], 1 - (1 - .006) ** 7)
        self.assertEqual(slowing['validation_status'], 'simulator_defined_not_trained_or_clinically_validated')

    def test_unsupported_or_missing_measurement_never_becomes_normal_motion(self):
        missing = predict({'fatigue_7d_mean': 2}, {'status': 'unavailable'})
        self.assertIsNone(missing['value'])
        self.assertFalse(missing['video_used'])
        for ratio in (.6, float('nan'), -1, 2):
            with self.assertRaises(ValueError):
                predict({'fatigue_7d_mean': 2}, self.measurement(0) | {'late_speed_ratio': ratio})
        with self.assertRaises(ValueError):
            predict({'fatigue_7d_mean': 2}, self.measurement(0) | {'motion_state': 1})
        for fatigue in (0, 6, float('inf')):
            with self.assertRaises(ValueError):
                event_probability(fatigue, 0)

    def test_paired_dataset_cutoffs_repeatability_and_future_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            episodes = generate(data / 'demo')
            first = (data / 'demo/runtime/episodes.json').read_bytes()
            generate(data / 'demo')
            self.assertEqual(first, (data / 'demo/runtime/episodes.json').read_bytes())
            features = json.loads((DATA / 'demo/runtime/video_features.json').read_text())
            (data / 'demo/runtime/video_features.json').write_text(json.dumps(features))
            result = get_paired_demo(data, RUNTIME)
            future = json.loads((data / 'demo/offline/future_events.json').read_text())
            for row, outcome in zip(episodes, future):
                as_of = datetime.fromisoformat(row['as_of'])
                self.assertLess(datetime.fromisoformat(row['reference_recorded_at']), as_of)
                self.assertEqual(outcome['followup_end'], (as_of + timedelta(hours=168)).isoformat())
                self.assertEqual(outcome['label_7d'], int(bool(outcome['events'])))
                for event in outcome['events']:
                    self.assertTrue(as_of < datetime.fromisoformat(event['at']) <= as_of + timedelta(hours=168))
                measured = result['cases'][int(row['id'][-2:]) - 1]['probability']['value']
                self.assertAlmostEqual(measured, outcome['generator_probability'])
            (data / 'demo/offline/future_events.json').write_text('{"future_poison": 99999}')
            self.assertEqual(result, get_paired_demo(data, RUNTIME))
            serialized = json.dumps(result)
            for field in ('generator_probability', 'label_7d', 'future_event', 'days_lost'):
                self.assertNotIn(field, serialized)
            self.assertIsNone(result['injury_probability'])

    def test_changed_video_or_bad_cutoff_rejects_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            generate(data / 'demo')
            features = json.loads((DATA / 'demo/runtime/video_features.json').read_text())
            features['clips']['S001']['video_sha256'] = 'changed'
            (data / 'demo/runtime/video_features.json').write_text(json.dumps(features))
            with self.assertRaisesRegex(ValueError, 'Video bytes changed'):
                get_paired_demo(data, RUNTIME)
            features['clips']['S001']['video_sha256'] = sha(RUNTIME / 'S001/video.mp4')
            (data / 'demo/runtime/video_features.json').write_text(json.dumps(features))
            path = data / 'demo/runtime/episodes.json'
            value = json.loads(path.read_text())
            value['episodes'][0]['history']['cutoff'] = '2026-01-25'
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'cutoff'):
                get_paired_demo(data, RUNTIME)

    def test_hosted_analyst_auth_and_missing_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'state.sqlite3')
            with patch.object(api, 'Store', return_value=store), patch.object(api, 'LOCAL_ONLY', False), patch.object(api, 'ANALYST_TOKEN', 'test-secret'):
                with TestClient(api.app) as client:
                    self.assertEqual(client.get('/api/demo/paired').status_code, 403)
                    headers = {'X-Analyst-Token': 'test-secret'}
                    self.assertEqual(client.get('/api/demo/paired', headers=headers).status_code, 200)
                    with patch('src.backend.demo_probability.get_paired_demo', side_effect=FileNotFoundError):
                        self.assertEqual(client.get('/api/demo/paired', headers=headers).status_code, 503)


if __name__ == '__main__':
    unittest.main()
