"""Write reproducible, cutoff-safe synthetic summaries; does not invoke a model."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.backend.config import DATA
from src.backend.history import get_history_summary
from src.backend.tools import mapping

meta = mapping('S001')
history = get_history_summary(meta['player_id'], meta['match_date'])
path = DATA / 'processed' / 'P001_2026-01-24.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(history, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
print(path)
