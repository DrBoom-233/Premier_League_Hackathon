import asyncio
import hmac
import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ANALYST_TOKEN, DEPLOYMENT, LOCAL_ONLY, ROOT, RUNTIME
from .schemas import AnalysisRequest
from .store import Store, utc
from .tools import clip_context, mapping, revision, safe_file
from .workflow import execute
from .access import code_digest, configured_codes
from .featured import featured_cases


def analyst_access(x_analyst_token: str = Header(default='')):
    if not LOCAL_ONLY and (not ANALYST_TOKEN or not hmac.compare_digest(x_analyst_token, ANALYST_TOKEN)):
        raise HTTPException(403, 'Analyst token required')


def analysis_access(x_analysis_code: str = Header(default=''), x_analyst_token: str = Header(default='')):
    if LOCAL_ONLY or (ANALYST_TOKEN and hmac.compare_digest(x_analyst_token, ANALYST_TOKEN)):
        return None
    digest = code_digest(x_analysis_code)
    if not x_analysis_code or digest not in configured_codes():
        raise HTTPException(403, 'Enter a valid analysis code to run a new analysis')
    return digest


def public_case(case, audience):
    if audience == 'analyst':
        return case
    frame_evidence = {k: v for k, v in case.get('evidence', {}).items() if v['kind'] == 'frame'}
    fan = case.get('narratives', {}).get('fan')
    # The fan API never returns specialist history, case concern or investigator text.
    return {k: v for k, v in case.items() if k in (
        'id', 'scenario_id', 'player_id', 'state', 'input_revision', 'created_at', 'completed_at',
        'elapsed_seconds', 'human_review_status', 'mode')} | {
        'evidence': frame_evidence, 'narratives': {'fan': fan} if fan else {},
        'injury_probability': None, 'probability_status': 'not_validated',
        'error': 'Analysis incomplete; see analyst diagnostics.' if case.get('error') else None,
        'calls': [{k: v for k, v in call.items() if k in ('role', 'status', 'latency_seconds', 'cache_hit', 'image_count')}
                  for call in case.get('calls', [])]}


@asynccontextmanager
async def lifespan(app):
    if not LOCAL_ONLY and not ANALYST_TOKEN:
        raise RuntimeError('Hosted mode requires PITCHGUARD_ANALYST_TOKEN')
    cloud = bool(os.environ.get('PITCHGUARD_STORAGE_ACCOUNT_URL'))
    if cloud:
        from .cloud import make_store
        store = make_store()
    else:
        store = Store()
    store.recover()
    store.configure_codes(configured_codes())
    app.state.store = store
    app.state.queue = asyncio.Queue()

    async def worker():
        while True:
            case_id = await app.state.queue.get()
            try:
                await execute(store.get(case_id), store)
            finally:
                app.state.queue.task_done()

    if os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING'):
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor()
    task = None if cloud else asyncio.create_task(worker(), name='bounded-analysis-worker')
    yield
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    if cloud:
        store.close()


app = FastAPI(title='PitchGuard AI', version='0.1.0', lifespan=lifespan)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'model_configured': bool(DEPLOYMENT and os.environ.get('AZURE_OPENAI_API_KEY')),
            'deployment': DEPLOYMENT, 'local_only': LOCAL_ONLY, 'data_mode': 'synthetic'}


@app.get('/api/scenarios')
def scenarios():
    value = mapping('S001')
    result = []
    for sid in value['scenarios']:
        try:
            _, _, clip, _, _ = clip_context(sid)
            video = (RUNTIME / sid / 'video.mp4').is_file()
            available, reason = True, None
        except (ValueError, OSError, KeyError):
            clip, video, available, reason = {}, False, False, 'Runtime assets unavailable; rebuild animation.'
        result.append({'id': sid, 'name': f'Replay {sid[-1]}', 'player_id': value['player_id'],
                       'duration_ms': clip.get('duration_ms', 10000), 'match_start_ms': value['match_start_ms'],
                       'video_url': f'/api/media/{sid}/video' if video else None,
                       'reference_video_url': '/api/media/R001/video',
                       'available': available, 'reason': reason, 'history_cutoff': value['history_cutoff'],
                       'match_date': value['match_date'], 'mapping_note': value['mapping_note']})
    return result


@app.get('/api/demo/paired')
def paired_demo():
    from .demo_probability import get_paired_demo
    try:
        return get_paired_demo()
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, 'Paired demo unavailable. Rebuild demo data and measure the source videos.')


@app.get('/api/demo/featured')
def featured():
    return [{'id': case['id'], 'scenario_id': case['scenario_id'], 'state': case['state'],
             'created_at': case['created_at']} for case in featured_cases()]


@app.get('/api/access')
def access(code=Depends(analysis_access)):
    return app.state.store.code_status(code) if code else {'administrator': True, 'remaining': None}


@app.get('/api/scenarios/{scenario}/events')
def events(scenario: str):
    try:
        _, _, clip, _, _ = clip_context(scenario)
    except (ValueError, OSError, KeyError):
        raise HTTPException(404, 'Unknown/unavailable replay')
    return [{'id': scenario + ':start', 'clip_time_ms': 0, 'match_time_ms': clip['match_start_ms'],
             'text': 'Observation window begins'},
            {'id': scenario + ':end', 'clip_time_ms': clip['duration_ms'],
             'match_time_ms': clip['match_start_ms'] + clip['duration_ms'], 'text': 'Observation window ends'}]


@app.post('/api/analyses', status_code=202)
async def start(body: AnalysisRequest, code=Depends(analysis_access)):
    try:
        if os.environ.get('PITCHGUARD_STORAGE_ACCOUNT_URL'):
            await asyncio.to_thread(app.state.store.expire_stale)
        rev = await asyncio.to_thread(revision, body.scenario_id)
        case = {'id': uuid4().hex, 'scenario_id': body.scenario_id, 'player_id': body.player_id,
                'input_revision': rev, 'mode': body.mode, 'created_at': utc(), 'state': 'queued',
                'evidence': {}, 'calls': [], 'trace': [], 'branch_errors': {},
                'injury_probability': None, 'probability_status': 'not_validated'}
        result, created = app.state.store.create(case, body.client_request_id, code=code)
    except ValueError as error:
        raise HTTPException(409, str(error))
    except (OSError, KeyError):
        raise HTTPException(422, 'Runtime assets unavailable')
    if created:
        if os.environ.get('PITCHGUARD_STORAGE_ACCOUNT_URL'):
            from .cloud import dispatch_job
            try:
                result['execution_name'] = await dispatch_job(result['id'])
                # The Job can already be running; do not overwrite its newer state.
                app.state.store.patch(result['id'], {'execution_name': result['execution_name']})
            except ValueError as error:
                result.update(state='failed', error=str(error))
                app.state.store.save(result)
        else:
            await app.state.queue.put(result['id'])
    return {'case_id': result['id'], 'state': result['state'], 'cache_hit': not created,
            'allowance': app.state.store.code_status(code) if code else None,
            'url': '/api/analyses/' + result['id']}


def find_case(case_id):
    published = next((case for case in featured_cases() if case['id'] == case_id), None)
    if published:
        return published
    if os.environ.get('PITCHGUARD_STORAGE_ACCOUNT_URL'):
        app.state.store.expire_stale()
    try:
        return app.state.store.get(case_id)
    except KeyError:
        raise HTTPException(404, 'Unknown analysis')


@app.get('/api/analyses/{case_id}')
def get_case(case_id: str, audience: str = Query('fan', pattern='^(fan|analyst)$'),
             x_analyst_token: str = Header(default=''), x_analysis_code: str = Header(default='')):
    case = find_case(case_id)
    if audience == 'analyst' and not case.get('public_demo'):
        analysis_access(x_analysis_code, x_analyst_token)
    return public_case(case, audience)


@app.get('/api/analyses/{case_id}/evidence/{evidence_id}')
def evidence(case_id: str, evidence_id: str, audience: str = Query('fan', pattern='^(fan|analyst)$'),
             x_analyst_token: str = Header(default=''), x_analysis_code: str = Header(default='')):
    original = find_case(case_id)
    if audience == 'analyst' and not original.get('public_demo'):
        analysis_access(x_analysis_code, x_analyst_token)
    case = public_case(original, audience)
    if evidence_id not in case['evidence']:
        raise HTTPException(404, 'Evidence not available to this audience')
    return case['evidence'][evidence_id]


@app.post('/api/analyses/{case_id}/acknowledgements', dependencies=[Depends(analysis_access)])
def acknowledge(case_id: str):
    find_case(case_id)
    app.state.store.acknowledge(case_id)
    return {'recorded': True, 'meaning': 'Human viewed this analysis; not a truth/health label.'}


@app.get('/api/media/{clip_id}/{asset_id}')
def media(clip_id: str, asset_id: str):
    if clip_id not in ('S001', 'S002', 'S003', 'S004', 'S006', 'R001'):
        raise HTTPException(404)
    from scripts.animation.run_vlm import load_clip
    try:
        base, clip = load_clip(RUNTIME, clip_id)
        if asset_id == 'video':
            return FileResponse(safe_file(base, clip['video_path']), media_type='video/mp4')
        frame = next((f for f in clip['frames'] if f['frame_id'] == asset_id), None)
        if frame is None:
            raise ValueError('Unknown frame')
        return FileResponse(safe_file(base, frame['path']), media_type='image/png')
    except (OSError, ValueError, KeyError):
        raise HTTPException(404, 'Media unavailable')


DIST = ROOT / 'src' / 'frontend' / 'dist'
if DIST.is_dir():
    app.mount('/', StaticFiles(directory=DIST, html=True), name='frontend')
