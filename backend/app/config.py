from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def setting(key: str, default: str = '') -> str:
    return os.environ.get(key, default)


def is_cloud() -> bool:
    return setting('APP_MODE', 'memory') == 'firestore'


def is_live_ai() -> bool:
    return setting('AI_MODE', 'mock') == 'adk'


def signoff_path() -> Path:
    return ROOT / setting('POLICY_SIGNOFF_PATH', 'policy/contract_approval.json')
