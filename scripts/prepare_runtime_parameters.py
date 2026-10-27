"""Prepare private ARM parameters without printing model keys or judge codes."""
import hashlib
import json
import secrets
import sys
from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
state = root / '.state'
state.mkdir(exist_ok=True)
foundation = json.loads((root.parent / 'foundation.outputs.json').read_text(encoding='utf-8-sig'))
access_path = state / 'access-secrets.json'
if not access_path.exists():
    access_path.write_text(json.dumps({
        'analyst_token': secrets.token_urlsafe(32),
        'judge_codes': {f'judge-{i}': 'PG-' + secrets.token_urlsafe(18) for i in range(1, 4)},
        'deployment_test_code': 'CHECK-' + secrets.token_urlsafe(18),
    }, indent=2), encoding='utf-8')
access = json.loads(access_path.read_text(encoding='utf-8'))
codes = {hashlib.sha256(code.encode()).hexdigest(): 10 for code in access['judge_codes'].values()}
codes[hashlib.sha256(access['deployment_test_code'].encode()).hexdigest()] = 1
settings = dotenv_values(root / '.env')
if not settings.get('AZURE_OPENAI_API_KEY'):
    raise SystemExit('Existing Foundry key is missing; no parameters written.')
parameters = {key: {'value': foundation[key]['value']} for key in (
    'registryServer', 'environmentId', 'storageUrl', 'apiIdentityId', 'apiClientId',
    'apiPrincipalId', 'workerIdentityId', 'workerClientId', 'insightsConnection')}
parameters.update({key: {'value': value} for key, value in {
    'location': 'francecentral', 'prefix': 'pgdemo',
    'image': foundation['registryServer']['value'] + '/pitchguard:' + (sys.argv[1] if len(sys.argv) > 1 else '20261026-v1'),
    'modelEndpoint': settings['AZURE_OPENAI_ENDPOINT'],
    'modelDeployment': settings['AZURE_OPENAI_DEPLOYMENT'],
    'modelKey': settings['AZURE_OPENAI_API_KEY'],
    'analystToken': access['analyst_token'], 'analysisCodes': json.dumps(codes),
}.items()})
document = {'$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#',
            'contentVersion': '1.0.0.0', 'parameters': parameters}
(state / 'runtime.parameters.json').write_text(json.dumps(document), encoding='utf-8')
print('Prepared private parameters and three independent 10-analysis judge codes; no secrets printed.')
