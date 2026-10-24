import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env', override=False)
DATA = Path(os.environ.get('PITCHGUARD_DATA_DIR', ROOT / 'data')).resolve()
STATE = Path(os.environ.get('PITCHGUARD_STATE_DIR', ROOT / '.state')).resolve()
RUNTIME = DATA / 'animation' / 'runtime'
DEPLOYMENT = os.environ.get('AZURE_OPENAI_DEPLOYMENT', '')
LOCAL_ONLY = os.environ.get('PITCHGUARD_LOCAL_ONLY', 'true').lower() == 'true'
ANALYST_TOKEN = os.environ.get('PITCHGUARD_ANALYST_TOKEN', '')
DEADLINE_SECONDS = 180
MAX_CALLS = 6
PROMPT_REVISION = 'pitchguard-evidence-v1'
