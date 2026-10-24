import asyncio
import hashlib
import json
import os
import time
from urllib.parse import quote, urlsplit

import httpx

from .config import DEPLOYMENT, PROMPT_REVISION
from .store import Store
from .schemas import Decision, HistoryOutput, MotionOutput, Narrative, SingleOutput


def emit_span(event, case_id):
    from opentelemetry import trace
    span = trace.get_tracer('pitchguard').start_span('agent.' + event['role'],
                start_time=int(event['started_at'] * 1_000_000_000))
    for key in ('role', 'status', 'cache_hit', 'image_count'):
        span.set_attribute('pitchguard.' + key, event[key])
    span.set_attribute('pitchguard.case_id', case_id)
    span.end()


class Model:
    def __init__(self, store: Store, case):
        self.store, self.case = store, case

    async def call(self, role, instruction, content, tools=None):
        if len(self.case['calls']) >= 6:
            raise ValueError('Case invocation limit exhausted')
        images = sum(c.get('type') == 'image_url' for c in content)
        if images > 10:
            raise ValueError('Image budget exceeds ten')
        endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT', '').rstrip('/')
        parsed = urlsplit(endpoint)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.path or not parsed.hostname.endswith(('.openai.azure.com', '.services.ai.azure.com'))):
            raise ValueError('Configure a resource-root Azure HTTPS endpoint')
        if not DEPLOYMENT or not os.environ.get('AZURE_OPENAI_API_KEY'):
            raise ValueError('Azure model configuration missing')
        payload = {'messages': [{'role': 'system', 'content': instruction}, {'role': 'user', 'content': content}],
                   'max_completion_tokens': 900, 'temperature': 0,
                   'response_format': {'type': 'json_object'}}
        contracts = {'history': HistoryOutput, 'motion': MotionOutput, 'motion_recheck': MotionOutput,
                     'investigator': Decision, 'investigator_final': Decision, 'narrative': Narrative,
                     'single_agent': SingleOutput, 'single_final': SingleOutput}
        if role in contracts:
            # Azure supports a subset; bounds remain enforced by the local Pydantic contract.
            def wire_schema(item):
                if isinstance(item, list):
                    return [wire_schema(v) for v in item]
                if isinstance(item, dict):
                    return {k: wire_schema(v) for k, v in item.items() if k not in (
                        'minLength', 'maxLength', 'minItems', 'maxItems', 'minimum', 'maximum',
                        'exclusiveMinimum', 'exclusiveMaximum', 'pattern', 'title')}
                return item
            schema = wire_schema(contracts[role].model_json_schema())
            if role == 'motion_recheck':
                schema['properties']['requested_recheck'] = {'type': 'null'}
            payload['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': contracts[role].__name__, 'strict': True, 'schema': schema}}
        if tools:
            payload.update(tools=tools, tool_choice='auto', parallel_tool_calls=False)
        version = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-10-21')
        key = hashlib.sha256(json.dumps([endpoint, version, DEPLOYMENT, PROMPT_REVISION, payload], sort_keys=True).encode()).hexdigest()
        cached = self.store.cached(key)
        event = {'role': role, 'started_at': time.time(), 'image_count': images, 'cache_hit': cached is not None,
                 'request_sha256': key, 'status': 'running'}
        self.case['calls'].append(event)
        self.store.save(self.case)
        started = time.perf_counter()
        if cached:
            event.update(status='completed', latency_seconds=0, usage=cached.get('usage'), cost_usd=0,
                         cost_status='cache_no_new_model_charge', source_inference=True)
            emit_span(event, self.case['id'])
            return cached
        # Reserve above measured 10-image smoke-test use; failed/unknown calls retain reservation.
        reserve_tokens = images * 2000 + sum(len(c.get('text', '')) for c in content) + len(instruction) + 900
        if reserve_tokens > 40000:
            event.update(status='failed', error='Input token reserve exceeds per-call budget')
            raise ValueError('Input too large')
        try:
            usage_id = self.store.reserve(self.case['id'], role, reserve_tokens)
        except ValueError:
            event.update(status='blocked', error='Call/token budget exhausted', cost_status='not_called')
            self.store.save(self.case)
            emit_span(event, self.case['id'])
            raise
        url = endpoint + '/openai/deployments/' + quote(DEPLOYMENT, safe='') + '/chat/completions?api-version=' + quote(version, safe='')
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
                response = await client.post(url, headers={'api-key': os.environ['AZURE_OPENAI_API_KEY']}, json=payload)
                if response.status_code >= 400:
                    raise ValueError(f'Azure HTTP {response.status_code}; no automatic retry')
                raw = response.json()
            choice = raw['choices'][0]
            if choice['finish_reason'] not in ('stop', 'tool_calls'):
                raise ValueError('Model output truncated or filtered')
            usage = raw.get('usage', {})
            self.store.finish(usage_id, usage.get('total_tokens'), 'completed')
            cost = None
            rate_in, rate_out = os.environ.get('PITCHGUARD_INPUT_USD_PER_MILLION'), os.environ.get('PITCHGUARD_OUTPUT_USD_PER_MILLION')
            if rate_in and rate_out and 'prompt_tokens' in usage and 'completion_tokens' in usage:
                cost = (usage['prompt_tokens'] * float(rate_in) + usage['completion_tokens'] * float(rate_out)) / 1_000_000
            event.update(status='completed', latency_seconds=round(time.perf_counter() - started, 3), usage=usage,
                         cost_usd=cost, cost_status='configured_rate_estimate' if cost is not None else 'unknown_rates')
            self.store.cache(key, raw)
            return raw
        except asyncio.CancelledError:
            event.update(status='cancelled', cost_status='unknown_inflight_charge', latency_seconds=round(time.perf_counter()-started, 3))
            raise
        except Exception as error:
            self.store.finish(usage_id, None, 'failed_or_unknown')
            event.update(status='failed', error=str(error) if isinstance(error, ValueError) else type(error).__name__,
                         cost_status='unknown', latency_seconds=round(time.perf_counter() - started, 3))
            raise ValueError(event['error']) from None
        finally:
            emit_span(event, self.case['id'])
            self.store.save(self.case)


def text_content(value):
    return [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False, allow_nan=False)}]


def parse(raw, contract):
    return contract.model_validate_json(raw['choices'][0]['message']['content'])
