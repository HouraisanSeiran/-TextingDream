"""Shared locations for the production save; importing this module writes nothing."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAVE_DIR = ROOT / 'saves'
SAVE_DB = SAVE_DIR / 'textiledream.sqlite3'


def save_db(root=ROOT):
    """Resolve the same production layout for an explicit project/test root."""
    return root / SAVE_DB.relative_to(ROOT)
