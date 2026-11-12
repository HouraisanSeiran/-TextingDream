"""Test defaults: enable civ-atlas so legacy import/native fixtures keep working.

Production default remains off (`TEXTILE_CIV_ATLAS` unset / ``0``). Individual tests that
assert the disabled path must ``monkeypatch.delenv`` / set ``0``.
"""
import os

# Applied at collection time so unittest and pytest both see it.
os.environ.setdefault('TEXTILE_CIV_ATLAS', '1')
