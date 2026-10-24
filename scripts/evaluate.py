"""Run a bounded REAL Azure integration set; output is not human-scored accuracy."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend.config import DATA
from src.backend.store import Store, utc
from src.backend.tools import revision
from src.backend.workflow import execute


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Make billable calls if not cached')
    parser.add_argument('--scenario', nargs='+', choices=['S001','S002','S003'], default=['S001','S002','S003'])
    parser.add_argument('--mode', choices=['multi','single'], default='multi')
    args = parser.parse_args()
    if not args.run:
        print('Use --run to authorize up to six calls per scenario (daily budgets also apply).')
        return
    store = Store()
    output = []
    for sid in args.scenario:
        case = {'id': uuid4().hex, 'scenario_id': sid, 'player_id': 'P001', 'input_revision':revision(sid),
                'mode':args.mode, 'created_at':utc(), 'state':'queued', 'evidence':{}, 'calls':[], 'trace':[], 'branch_errors':{}}
        case, created = store.create(case,uuid4().hex)
        if created:
            await execute(case,store)
        output.append({'case_id':case['id'],'scenario_id':sid,'mode':args.mode,'state':case['state'],
                       'elapsed_seconds':case.get('elapsed_seconds'), 'call_count':len(case['calls']),
                       'calls':case['calls'],'concern':case.get('decision',{}).get('concern'),
                       'view_status':case.get('motion_output',{}).get('view_status'),
                       'recheck_requested':bool(case.get('recheck_request')), 'branch_errors':case['branch_errors'],
                       'error':case.get('error'),'human_review_status':'pending', 'input_revision':case['input_revision']})
        print(json.dumps(output[-1],ensure_ascii=False),flush=True)
    path = DATA/'animation'/'evaluation'/'results'/f'integration_{args.mode}_{__import__("time").time_ns()}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Saved:',path)


if __name__=='__main__':
    asyncio.run(main())
