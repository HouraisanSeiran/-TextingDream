# -*- coding: utf-8 -*-
"""Isolated civ-atlas backend for 织梦 (opt-in; disabled by default).

All civ-atlas-specific Python lives in this package. Compatibility shims under
``app.civ_atlas_snapshot`` / ``app.civ_atlas_history`` / ``app.civ_exploration`` /
``app.native_worlds`` / ``app.native_starts`` / ``app.world_source_civ_atlas`` re-export
these modules so older imports keep working.

Runtime / HTTP entry points must call :func:`app.map_policy.require_civ_atlas` (or
:func:`require`) before serving civ-atlas data. The upstream front-end remains under
``external/civ-atlas`` and is also gated when this backend is off.
"""
from ..map_policy import CivAtlasDisabled, civ_atlas_enabled, require_civ_atlas

require = require_civ_atlas
enabled = civ_atlas_enabled
Disabled = CivAtlasDisabled

#: Modules that belong exclusively to this backend (for docs / audits).
MODULES = (
    'app.civ_atlas.snapshot',
    'app.civ_atlas.history',
    'app.civ_atlas.exploration',
    'app.civ_atlas.world_source',
    'app.civ_atlas.native_worlds',
    'app.civ_atlas.native_starts',
)

__all__ = [
    'CivAtlasDisabled', 'Disabled', 'MODULES',
    'civ_atlas_enabled', 'enabled', 'require', 'require_civ_atlas',
]
