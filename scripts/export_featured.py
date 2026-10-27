"""Export selected real synthetic cases, excluding private runtime diagnostics."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'id', 'scenario_id', 'player_id', 'input_revision', 'mode', 'created_at', 'state',
          'completed_at', 'elapsed_seconds', 'human_review_status', 'history', 'history_output',
          'motion_output', 'decision', 'narratives', 'evidence', 'recheck_request',
          'injury_probability', 'probability_status'}
CALL_FIELDS = {'role', 'status', 'cache_hit', 'latency_seconds', 'image_count', 'cost_status', 'cost_usd'}


def export(databases):
    cases = {}
    for database in databases:
        with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
            for (payload,) in db.execute("SELECT payload FROM cases WHERE state='completed' AND mode='multi' ORDER BY created DESC"):
                source = json.loads(payload)
                if source['scenario_id'] in cases:
                    continue
                # Never publish evidence for a different version of the rendered video frames.
                for evidence in source.get('evidence', {}).values():
                    if evidence['kind'] != 'frame':
                        continue
                    path = ROOT / 'data' / 'animation' / 'runtime' / evidence['clip_id'] / evidence['path']
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != evidence['source_sha256']:
                        break
                else:
                    item = {k: v for k, v in source.items() if k in FIELDS}
                    item['calls'] = [{k: v for k, v in call.items() if k in CALL_FIELDS} for call in source['calls']]
                    item['public_demo'] = True
                    cases[source['scenario_id']] = item
    output = ROOT / 'data' / 'demo' / 'runtime' / 'featured_cases.json'
    output.write_text(json.dumps(list(cases.values()), indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'exported_scenarios': list(cases), 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('databases', type=Path, nargs='+')
    export(parser.parse_args().databases)
