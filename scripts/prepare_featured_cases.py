"""Run each new featured replay once; failures are recorded, never automatically retried."""
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend.store import Store, utc
from src.backend.tools import revision
from src.backend.workflow import execute


async def main():
    store = Store()
    for scenario in ('S006', 'S004'):
        item = {'id': uuid4().hex, 'scenario_id': scenario, 'player_id': 'P001',
                'input_revision': revision(scenario), 'mode': 'multi', 'created_at': utc(),
                'state': 'queued', 'evidence': {}, 'calls': [], 'trace': [], 'branch_errors': {}}
        item, created = store.create(item, uuid4().hex)
        if created:
            await execute(item, store)
        print(json.dumps({'scenario': scenario, 'id': item['id'], 'state': item['state'],
                          'elapsed_seconds': item.get('elapsed_seconds'), 'error': item.get('error'),
                          'new_model_calls': sum(not c['cache_hit'] for c in item['calls'])}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
