# -*- coding: utf-8 -*-
"""Player-map backend policy: Terragenesis by default; civ-atlas opt-in.

Environment
-----------
``TEXTILE_CIV_ATLAS``
    ``0`` / ``false`` / ``off`` / unset → civ-atlas disabled (default).
    ``1`` / ``true`` / ``on`` → civ-atlas imports, native host, and ``mechanics.map.kind=civ_atlas`` allowed.

``TEXTILE_DEFAULT_WORLD_MAP``
    Relative product directory under the repo root used when a story has no ``mechanics.map``.
    Default: ``artifacts/fast-world/tg-speed-archipelago-1600-20261108``.

``TEXTILE_DEFAULT_WORLD_IDENTITY``
    Optional override of the pinned product identity hash. When unset, read from
    ``manifest.json`` beside the default product (or the baked fallback identity).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .paths import ROOT

#: Baked identity for the shipped TG speed product (also in TG-SPEED-EVIDENCE.md).
_FALLBACK_IDENTITY = (
    'db09ec0f6a166d311a0055adeee3601868e618f81e7cdc92f28117524fcbc199'
)
_DEFAULT_PRODUCT = 'artifacts/fast-world/tg-speed-archipelago-1600-20261108'

_TRUTHY = {'1', 'true', 'on', 'yes', 'enable', 'enabled'}
_FALSY = {'0', 'false', 'off', 'no', 'disable', 'disabled', ''}


class CivAtlasDisabled(RuntimeError):
    """Raised when a civ-atlas entry point is hit while the backend is off."""

    def __init__(self, detail=''):
        msg = ('civ-atlas 后端当前已禁用。设置环境变量 TEXTILE_CIV_ATLAS=1 后重启服务即可开启。'
               + ((' ' + detail) if detail else ''))
        super().__init__(msg)
        self.detail = detail


def civ_atlas_enabled(environ=None) -> bool:
    env = environ if environ is not None else os.environ
    raw = str(env.get('TEXTILE_CIV_ATLAS', '0')).strip().lower()
    if raw in _TRUTHY:
        return True
    if raw in _FALSY:
        return False
    return False


def require_civ_atlas(detail='', *, environ=None):
    if not civ_atlas_enabled(environ):
        raise CivAtlasDisabled(detail)


def default_product_path(environ=None) -> str:
    env = environ if environ is not None else os.environ
    path = (env.get('TEXTILE_DEFAULT_WORLD_MAP') or _DEFAULT_PRODUCT).strip().replace('\\', '/')
    if not path or '..' in Path(path).parts:
        return _DEFAULT_PRODUCT
    return path


def _read_identity(repo_root: Path, product_rel: str) -> str:
    manifest = repo_root / product_rel / 'manifest.json'
    if not manifest.is_file():
        return _FALLBACK_IDENTITY
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return _FALLBACK_IDENTITY
    identity = data.get('identity') or data.get('product_identity')
    if isinstance(identity, str) and len(identity) >= 16:
        return identity
    return _FALLBACK_IDENTITY


def default_world_identity(repo_root=None, environ=None) -> str:
    env = environ if environ is not None else os.environ
    override = (env.get('TEXTILE_DEFAULT_WORLD_IDENTITY') or '').strip()
    if len(override) >= 16:
        return override
    root = Path(repo_root) if repo_root is not None else ROOT
    return _read_identity(root, default_product_path(env))


def default_product_exists(repo_root=None, environ=None) -> bool:
    root = Path(repo_root) if repo_root is not None else ROOT
    return (root / default_product_path(environ) / 'manifest.json').is_file()


def default_player_map_raw(repo_root=None, environ=None, *, reveal_radius_km=300.0):
    """``mechanics.map`` object for Terragenesis, or ``None`` if the product is absent."""
    if not default_product_exists(repo_root, environ):
        return None
    return {
        'kind': 'world_map_product',
        'product_path': default_product_path(environ),
        'product_identity': default_world_identity(repo_root, environ),
        'fog': {'reveal_radius_km': float(reveal_radius_km)},
    }


def status(repo_root=None, environ=None) -> dict:
    root = Path(repo_root) if repo_root is not None else ROOT
    product = default_product_path(environ)
    return {
        'civ_atlas_enabled': civ_atlas_enabled(environ),
        'default_map_kind': 'world_map_product',
        'default_product_path': product,
        'default_product_present': default_product_exists(root, environ),
        'default_product_identity': default_world_identity(root, environ)[:16] + '…',
        'enable_hint': 'TEXTILE_CIV_ATLAS=1',
    }
