"""Only explicitly exported, synthetic demonstration cases are public."""
import json

from .config import DATA


def featured_cases():
    path = DATA / 'demo' / 'runtime' / 'featured_cases.json'
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding='utf-8'))
