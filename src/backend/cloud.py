"""Optional Blob-backed state and finite Container Apps Job dispatch."""
import asyncio
import copy
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

from .store import Store


class BlobStore(Store):
    """shortcut: one small SQLite snapshot under a Blob lease, replace for multi-user scale."""
    def __init__(self):
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobClient
        from azure.core.exceptions import ResourceExistsError
        self.credential = DefaultAzureCredential()
        self.blob = BlobClient(os.environ['PITCHGUARD_STORAGE_ACCOUNT_URL'],
                               os.environ.get('PITCHGUARD_STORAGE_CONTAINER', 'pitchguard'),
                               'state/cases.sqlite3', credential=self.credential)
        self.directory = tempfile.TemporaryDirectory(prefix='pitchguard-state-')
        self.path = Path(self.directory.name) / 'state.sqlite3'
        # Initialize with the local implementation before the cloud override can run.
        Store(self.path)
        try:
            self.blob.upload_blob(self.path.read_bytes(), overwrite=False)
        except ResourceExistsError:
            pass

    @contextmanager
    def connect(self):
        from azure.core.exceptions import HttpResponseError
        lease = None
        # Short contention retry only for state locks; never retry a model call.
        for attempt in range(25):
            try:
                lease = self.blob.acquire_lease(lease_duration=60)
                break
            except HttpResponseError as error:
                if error.status_code != 409 or attempt == 24:
                    raise
                time.sleep(.2)
        try:
            self.path.write_bytes(self.blob.download_blob(lease=lease).readall())
            with Store.connect(self) as db:
                yield db
            self.blob.upload_blob(self.path.read_bytes(), overwrite=True, lease=lease)
        finally:
            if lease:
                lease.release()

    def recover(self):
        # Hosted app restarts must not mark a live finite Job as failed.
        return

    def close(self):
        self.blob.close()
        self.credential.close()
        self.directory.cleanup()


def make_store():
    return BlobStore() if os.environ.get('PITCHGUARD_STORAGE_ACCOUNT_URL') else Store()


async def dispatch_job(case_id):
    from azure.identity import DefaultAzureCredential
    resource = os.environ.get('PITCHGUARD_JOB_RESOURCE_ID', '')
    if not resource.startswith('/subscriptions/') or '/jobs/' not in resource:
        raise ValueError('Container Apps Job resource ID is not configured')
    credential = DefaultAzureCredential()
    try:
        token = await asyncio.to_thread(credential.get_token, 'https://management.azure.com/.default')
        url = 'https://management.azure.com' + resource
        headers = {'Authorization': 'Bearer ' + token.token}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url + '?api-version=2024-03-01', headers=headers)
            response.raise_for_status()
            template = copy.deepcopy(response.json()['properties']['template'])
            container = next(c for c in template['containers'] if c['name'] == 'worker')
            container['env'] = [e for e in container.get('env', []) if e['name'] != 'PITCHGUARD_CASE_ID']
            container['env'].append({'name': 'PITCHGUARD_CASE_ID', 'value': case_id})
            response = await client.post(url + '/start?api-version=2024-03-01', headers=headers, json={'template':template})
            response.raise_for_status()
            return response.json().get('name', 'accepted')
    except httpx.HTTPError:
        raise ValueError('Azure Job dispatch failed; case persisted, explicit retry required') from None
    finally:
        credential.close()


async def run_job():
    """Global execution lease prevents concurrent model workflows or duplicate Job charges."""
    from azure.core.exceptions import ResourceExistsError
    if os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING'):
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor()
    store = BlobStore()
    from azure.storage.blob import BlobClient
    lock = BlobClient(os.environ['PITCHGUARD_STORAGE_ACCOUNT_URL'],
                      os.environ.get('PITCHGUARD_STORAGE_CONTAINER', 'pitchguard'),
                      'state/inference.lock', credential=store.credential)
    try:
        lock.upload_blob(b'global-inference-lease', overwrite=False)
    except ResourceExistsError:
        pass
    lease = lock.acquire_lease(lease_duration=60)

    async def renew():
        while True:
            await asyncio.sleep(20)
            await asyncio.to_thread(lease.renew)

    task = asyncio.create_task(renew())
    try:
        case = store.get(os.environ['PITCHGUARD_CASE_ID'])
        if case['state'] != 'queued':
            return
        from .workflow import execute
        analysis = asyncio.create_task(execute(case, store))
        done, _ = await asyncio.wait({analysis, task}, return_when=asyncio.FIRST_COMPLETED)
        if task in done:
            analysis.cancel()
            await asyncio.gather(analysis, return_exceptions=True)
            case.update(state='failed', error='Execution lease renewal failed; no automatic retry')
            store.save(case)
            raise RuntimeError('Lease lost')
        await analysis
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        lease.release()
        lock.close()
        store.close()


if __name__ == '__main__':
    asyncio.run(run_job())
