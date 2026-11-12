"""Enable civ-atlas for the test suite (production default remains off)."""
import os

os.environ.setdefault('TEXTILE_CIV_ATLAS', '1')
