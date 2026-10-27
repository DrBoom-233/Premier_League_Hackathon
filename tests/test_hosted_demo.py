import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi.testclient import TestClient

from src.backend import app as api
from src.backend.access import code_digest
from src.backend.store import Store, utc


def case(number):
    return {'id': f'case-{number}', 'scenario_id': 'S001', 'player_id': 'P001',
            'input_revision': f'revision-{number}', 'mode': 'multi', 'created_at': utc(),
            'state': 'queued', 'evidence': {}, 'calls': [], 'narratives': {}}


class JudgeAllowanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'cases.sqlite3'
        self.store = Store(self.path)
        self.digest = code_digest('a-test-code')
        self.store.configure_codes({self.digest: 10})

    def test_ten_new_analyses_multiple_calls_restart_and_cached_reuse(self):
        for i in range(10):
            saved, created = self.store.create(case(i), f'request-{i}', code=self.digest)
            self.assertTrue(created)
            self.store.reserve(saved['id'], 'history', 1)
            self.store.reserve(saved['id'], 'motion', 1)
            saved['state'] = 'completed'
            self.store.save(saved)
        self.assertEqual(Store(self.path).code_status(self.digest)['used'], 10)
        with self.assertRaisesRegex(ValueError, 'allowance exhausted'):
            self.store.create(case(11), 'eleventh', code=self.digest)
        _, created = self.store.create(case(0), 'repeat-with-new-id', code=self.digest)
        self.assertFalse(created)
        self.assertEqual(self.store.code_status(self.digest)['used'], 10)

    def test_unstarted_failures_and_all_cached_work_do_not_consume(self):
        item, _ = self.store.create(case(1), 'one', code=self.digest)
        self.assertEqual(self.store.code_status(self.digest)['remaining'], 9)
        item.update(state='failed', error='Dispatch failed before any model request')
        self.store.save(item)
        self.assertEqual(self.store.code_status(self.digest)['remaining'], 10)
        item, _ = self.store.create(case(2), 'two', code=self.digest)
        item.update(state='completed')
        self.store.save(item)
        self.assertEqual(self.store.code_status(self.digest)['used'], 0)

    def test_failed_paid_request_is_counted_and_codes_are_independent(self):
        item, _ = self.store.create(case(1), 'one', code=self.digest)
        self.store.reserve(item['id'], 'history', 1)
        item.update(state='failed')
        self.store.save(item)
        second = code_digest('another-code')
        self.store.configure_codes({self.digest: 10, second: 10})
        self.assertEqual(self.store.code_status(self.digest)['remaining'], 9)
        self.assertEqual(self.store.code_status(second)['remaining'], 10)

    def test_parallel_requests_cannot_reserve_more_than_ten(self):
        def create(i):
            try:
                self.store.create(case(i), f'request-{i}', code=self.digest)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=8) as executor:
            self.assertEqual(sum(executor.map(create, range(20))), 10)
        self.assertEqual(self.store.code_status(self.digest)['pending'], 10)

    def test_lost_unstarted_job_releases_allowance_without_retry(self):
        item = case(1)
        item['created_at'] = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()
        self.store.create(item, 'lost-start', code=self.digest)
        self.store.expire_stale()
        self.assertEqual(self.store.get(item['id'])['state'], 'failed')
        self.assertEqual(self.store.code_status(self.digest)['remaining'], 10)

    def test_public_demo_reads_and_invalid_code_never_start_work(self):
        published = case('published') | {'public_demo': True, 'state': 'completed', 'history': {'synthetic': True}}
        with patch.object(api, 'Store', return_value=self.store), patch.object(api, 'LOCAL_ONLY', False), \
             patch.object(api, 'ANALYST_TOKEN', 'operator-secret'), \
             patch.object(api, 'featured_cases', return_value=[published]), \
             patch.dict('os.environ', {'PITCHGUARD_ANALYSIS_CODES': json.dumps({self.digest: 10})}):
            with TestClient(api.app) as client:
                self.assertEqual(client.get('/api/demo/paired').status_code, 200)
                self.assertEqual(client.get('/api/demo/featured').json()[0]['id'], published['id'])
                self.assertIn('history', client.get(f"/api/analyses/{published['id']}?audience=analyst").json())
                self.assertNotIn('history', client.get(f"/api/analyses/{published['id']}?audience=fan").json())
                response = client.post('/api/analyses', json={'scenario_id': 'S001', 'client_request_id': 'unauthorized'})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(self.store.list_cases(), [])
                self.assertEqual(client.get('/api/access', headers={'X-Analysis-Code': 'a-test-code'}).json()['remaining'], 10)
                self.assertEqual(client.get('/api/access', headers={'X-Analysis-Code': 'wrong'}).status_code, 403)


class AzureJobContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_uses_root_template_and_accepts_empty_202(self):
        from src.backend.cloud import dispatch_job
        template = {'containers': [{'name': 'worker', 'image': 'example/image:v1', 'env': [{'name': 'EXISTING', 'value': 'yes'}]}],
                    'initContainers': None, 'volumes': []}
        client = AsyncMock()
        request = httpx.Request('GET', 'https://management.azure.com/example')
        client.get.return_value = httpx.Response(200, json={'properties': {'template': template}}, request=request)
        client.post.return_value = httpx.Response(202, request=request)
        credential = Mock()
        credential.get_token.return_value = Mock(token='test-access-token')
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        with patch('azure.identity.DefaultAzureCredential', return_value=credential), \
             patch('src.backend.cloud.httpx.AsyncClient', return_value=manager), \
             patch.dict('os.environ', {'PITCHGUARD_JOB_RESOURCE_ID': '/subscriptions/test/resourceGroups/test/providers/Microsoft.App/jobs/worker'}):
            self.assertEqual(await dispatch_job('case-123'), 'accepted')
        payload = client.post.call_args.kwargs['json']
        self.assertNotIn('template', payload)
        self.assertNotIn('volumes', payload)
        self.assertNotIn('initContainers', payload)
        self.assertIn({'name': 'PITCHGUARD_CASE_ID', 'value': 'case-123'}, payload['containers'][0]['env'])
        self.assertEqual(len(template['containers'][0]['env']), 1)
        credential.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
