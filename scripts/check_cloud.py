"""Bounded external acceptance; --analyze uses only the separate one-use test code."""
import argparse
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx

root = Path(__file__).resolve().parents[1]
release = root.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analyze', action='store_true')
    args = parser.parse_args()
    outputs = json.loads((release / 'runtime.outputs.json').read_text(encoding='utf-8-sig'))
    base = outputs['demoUrl']['value']
    access = json.loads((root / '.state' / 'access-secrets.json').read_text())
    with httpx.Client(base_url=base, timeout=90) as client:
        response = client.get('/api/health'); response.raise_for_status()
        assert response.json()['local_only'] is False
        assert client.get('/api/demo/paired').json()['cases']
        featured = client.get('/api/demo/featured').json()
        assert len(featured) == 5
        item = client.get('/api/analyses/' + featured[0]['id'], params={'audience': 'analyst'})
        item.raise_for_status(); assert item.json()['public_demo'] is True
        fan = client.get('/api/analyses/' + featured[0]['id'], params={'audience': 'fan'}).json()
        assert 'history' not in fan and 'decision' not in fan
        media = client.get('/api/media/S006/video', headers={'Range': 'bytes=0-100'})
        assert media.status_code == 206 and len(media.content) == 101
        assert client.get('/.env').status_code == 404
        assert client.get('/api/access', headers={'X-Analysis-Code': 'invalid'}).status_code == 403
        assert client.post('/api/analyses', json={'scenario_id': 'S001', 'client_request_id': 'unauthorized-check'}).status_code == 403
        judge_remaining = []
        for code in access['judge_codes'].values():
            status = client.get('/api/access', headers={'X-Analysis-Code': code})
            status.raise_for_status(); judge_remaining.append(status.json()['remaining'])
        assert judge_remaining == [10, 10, 10], judge_remaining
        print(json.dumps({'public_checks': 'passed', 'url': base, 'featured_cases': len(featured),
                          'judge_allowances': judge_remaining}), flush=True)
        if not args.analyze:
            return
        headers = {'X-Analysis-Code': access['deployment_test_code']}
        request_path = root / '.state' / 'cloud-check-request.json'
        if not request_path.exists():
            request_path.write_text(json.dumps({'scenario_id': 'S001', 'client_request_id': uuid4().hex}))
        body = json.loads(request_path.read_text())
        response = client.post('/api/analyses', json=body, headers=headers)
        response.raise_for_status()
        started = response.json()
        (root / '.state' / 'cloud-check-start.json').write_text(json.dumps(started))
        print(json.dumps({'cloud_analysis': started}), flush=True)
        deadline = time.monotonic() + 480
        previous = None
        while time.monotonic() < deadline:
            response = client.get(started['url'], params={'audience': 'analyst'}, headers=headers)
            response.raise_for_status(); case = response.json()
            if case['state'] != previous:
                print(json.dumps({'state': case['state'], 'case_id': case['id']}), flush=True)
                previous = case['state']
            if case['state'] not in ('queued', 'running'):
                (root / '.state' / 'cloud-check-result.json').write_text(json.dumps(case, indent=2))
                status = client.get('/api/access', headers=headers).json()
                summary = {'state': case['state'], 'case_id': case['id'], 'error': case.get('error'),
                           'calls': [{'role': c['role'], 'status': c['status']} for c in case['calls']],
                           'test_allowance': status}
                print(json.dumps(summary), flush=True)
                assert case['state'] in ('completed', 'degraded'), summary
                assert status['used'] == 1 and status['remaining'] == 0, status
                again = client.post('/api/analyses', json=body, headers=headers)
                again.raise_for_status(); assert again.json()['cache_hit']
                assert again.json()['case_id'] == case['id']
                return
            time.sleep(3)
        raise RuntimeError('Timed out waiting for cloud Job; no automatic paid retry')


if __name__ == '__main__':
    main()
