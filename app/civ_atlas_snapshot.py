# -*- coding: utf-8 -*-
"""Compatibility shim — implementation: :mod:`app.civ_atlas.snapshot`."""
from .civ_atlas.snapshot import *  # noqa: F401,F403
from .civ_atlas.snapshot import (  # noqa: F401
    BIOME_NAMES, CONTAINER_MAGIC, FORMAT, MAX_CONTAINER_BYTES,
    MapImportError, create_import, load_world, parse_container, preview_grid,
    preview_rgb, sample_region,
)
