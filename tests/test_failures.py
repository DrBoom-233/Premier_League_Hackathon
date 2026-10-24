import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_backend import FakeModel, new_case, raw
from src.backend.store import Store
from src.backend.workflow import execute


class FailureTests(unittest.TestCase):
    def run_case(self, factory):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory)/'db')
            case = new_case()
            store.create(case,'failure')
            return asyncio.run(execute(case,store,factory))

    def test_motion_unavailable_keeps_history_without_pretending_success(self):
        class Unavailable(FakeModel):
            async def call(self,role,instruction,content,tools=None):
                if role=='motion': raise ValueError('Azure HTTP 429')
                if role=='investigator':
                    assert tools is None
                    return raw({'concern':'routine','accepted_evidence_ids':['daily:P001:2026-01-24'],
                                'rejected_evidence_ids':[], 'rationale':[{'text':'Historical context only.', 'evidence_ids':['daily:P001:2026-01-24']}],
                                'limitations':['Visual evidence unavailable.']})
                return await super().call(role,instruction,content,tools)
        result=self.run_case(Unavailable)
        self.assertEqual(result['state'],'degraded')
        self.assertEqual(result['decision']['concern'],'insufficient_evidence')
        self.assertEqual(result['narratives']['fan']['statements'],[])
        self.assertNotIn('recheck_request',result)

    def test_invalid_model_json_is_failed_not_published(self):
        class Malformed(FakeModel):
            async def call(self,*args,**kwargs): return raw({'unexpected':'not a contract'})
        result=self.run_case(Malformed)
        self.assertEqual(result['state'],'failed')
        self.assertNotIn('narratives',result)

    def test_deadline_cancels_inflight_calls(self):
        class Hanging(FakeModel):
            async def call(self,*args,**kwargs): await asyncio.sleep(10)
        with patch('src.backend.workflow.DEADLINE_SECONDS',.03):
            result=self.run_case(Hanging)
        self.assertEqual(result['state'],'failed')
        self.assertEqual(result['error'],'TimeoutError')

    def test_changed_revision_is_rejected_without_call(self):
        class ShouldNotRun(FakeModel):
            async def call(self,*args,**kwargs): raise AssertionError('Must not be called')
        with patch('src.backend.workflow.revision',return_value='changed'):
            result=self.run_case(ShouldNotRun)
        self.assertEqual(result['state'],'failed')
        self.assertEqual(result['calls'],[])

    def test_forged_citation_stops_publication(self):
        class Forged(FakeModel):
            async def call(self,role,*args,**kwargs):
                value=await super().call(role,*args,**kwargs)
                if role=='investigator_final':
                    return raw({'concern':'review','accepted_evidence_ids':['S001_F9999'],
                        'rejected_evidence_ids':[],'rationale':[{'text':'Unsupported observation.', 'evidence_ids':['S001_F9999']}],
                        'limitations':[]})
                return value
        result=self.run_case(Forged)
        self.assertEqual(result['state'],'degraded')
        self.assertNotIn('narratives',result)

    def test_history_branch_failure_preserves_visual_result(self):
        with patch('src.backend.workflow.get_history',side_effect=OSError('missing history')):
            result=self.run_case(FakeModel)
        self.assertEqual(result['state'],'degraded')
        self.assertIn('motion_output',result)
        self.assertNotIn('history_output',result)


class BlobSnapshotTests(unittest.TestCase):
    def test_shared_durable_snapshot_and_lease_release_on_failure(self):
        from src.backend.cloud import BlobStore
        class Lease:
            def __init__(self,blob): self.blob=blob
            def release(self): self.blob.held=False
        class Download:
            def __init__(self,blob): self.blob=blob
            def readall(self): return self.blob.data
        class Blob:
            def __init__(self): self.data=None; self.held=False
            def upload_blob(self,data,overwrite=False,lease=None):
                from azure.core.exceptions import ResourceExistsError
                if self.data and not overwrite: raise ResourceExistsError('exists')
                self.data=data
            def download_blob(self,lease=None): return Download(self)
            def acquire_lease(self,lease_duration):
                assert not self.held
                self.held=True;return Lease(self)
            def close(self): pass
        blob=Blob()
        class Credential:
            def close(self): pass
        with patch('azure.storage.blob.BlobClient',return_value=blob),patch('azure.identity.DefaultAzureCredential',Credential),patch.dict('os.environ',{'PITCHGUARD_STORAGE_ACCOUNT_URL':'https://test.blob.core.windows.net'}):
            first=BlobStore();second=BlobStore()
            try:
                case=new_case();first.create(case,'cloud')
                self.assertEqual(second.get(case['id'])['state'],'queued')
                second.patch(case['id'],{'state':'completed'})
                self.assertEqual(first.get(case['id'])['state'],'completed')
                with self.assertRaises(ValueError):
                    with first.connect() as db:
                        db.execute("DELETE FROM cases")
                        raise ValueError('rollback')
                self.assertFalse(blob.held)
                self.assertEqual(second.get(case['id'])['state'],'completed')
            finally:
                first.close();second.close()


if __name__=='__main__': unittest.main()
