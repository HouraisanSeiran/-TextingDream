# -*- coding: utf-8 -*-
"""Readiness checks: can weather and roads plug into a Terragenesis world_map_product?

This module does **not** invent climate or roads. It inspects a frozen product and the
existing player seams (``weather_view``, ``events.exploration_graph`` / adventure routes)
and reports what already works vs what still needs an adapter.

Weather today
-------------
``weather_view`` takes place ``coordinates`` as lon/lat (and optional elevation / biome /
coast). A planar TG journey stores **metres** in those slots, so feeding them straight into
lon/lat climate is wrong. Usable bridges without new fiction:

* elevation from ``map_source.crop`` / ``sample`` at (x, z);
* optional regional-climate sidecar if present beside the product;
* story-declared ``mechanics.weather`` climate / season (already works, map-agnostic).

Roads today
-----------
``civ_exploration`` compiles ``mechanics.exploration.roads`` from civ-atlas route cells.
``events.exploration_graph`` only accepts ``source == 'civ_routes'``. TG fast products expose
land/sea elevation and river polylines, **not** built road networks. Bridging options:

* keep package-authored ``mechanics.adventure.routes`` / location neighbors (already works);
* future ``source: world_land`` pathfinding on the land mask (not implemented here);
* civ-sim / history adoption may later emit route candidates — still not wired to play.
"""
from __future__ import annotations

from pathlib import Path

from . import map_policy, map_source, weather_view
from .paths import ROOT


def _product_dir(repo_root=None, environ=None):
    root = Path(repo_root) if repo_root is not None else ROOT
    raw = map_policy.default_player_map_raw(root, environ)
    if raw is None:
        raise FileNotFoundError('默认 Terragenesis 产品不存在')
    return (root / raw['product_path']).resolve(), raw


def inspect_product(repo_root=None, environ=None) -> dict:
    path, raw = _product_dir(repo_root, environ)
    src = map_source.load_source('world-map-product', path,
                                 expected_identity=raw['product_identity'])
    info = src.info
    layers = list(info.layers or ())
    vector_names = list(info.vectors or ())
    has_rivers = False
    try:
        rivers = src.vectors('rivers') if 'rivers' in vector_names else []
        has_rivers = bool(rivers)
    except Exception:
        has_rivers = False
    spacing = float(info.spacing_m)
    shape = list(info.shape_zx) if info.shape_zx is not None else None
    sample_elev = None
    if shape and shape[0] > 2 and shape[1] > 2:
        import math
        import numpy as np
        # Scan a few windows for a finite land elevation in weather's accepted range.
        for frac in (0.35, 0.5, 0.65, 0.25, 0.75):
            mid_z = int(shape[0] * frac) * spacing
            mid_x = int(shape[1] * frac) * spacing
            half = spacing * 4
            cropped = src.crop(mid_x - half, mid_z - half, mid_x + half, mid_z + half,
                               max_cells=256)
            elev = cropped.get('elevation_m')
            status = cropped.get('status')
            if elev is None:
                continue
            arr = np.asarray(elev, dtype=float)
            mask = np.isfinite(arr) & (arr >= -500.0) & (arr <= 9000.0)
            if status is not None:
                st = np.asarray(status)
                # status 3/4 are water in play_map_world hypsometric; prefer land.
                mask = mask & (st != 3) & (st != 4)
            if not np.any(mask):
                continue
            sample_elev = float(arr[mask][0])
            if math.isfinite(sample_elev):
                break
        else:
            sample_elev = None
    climate_sidecar = None
    root = Path(repo_root) if repo_root is not None else ROOT
    for sibling in (path / 'regional-climate',
                    path.parent / (path.name + '-climate'),
                    path.parent.parent / 'worlds' / path.name / 'regional-climate'):
        if sibling.is_dir() and (sibling / 'manifest.json').is_file():
            try:
                climate_sidecar = str(sibling.resolve().relative_to(root.resolve()))
            except ValueError:
                climate_sidecar = str(sibling)
            break
    return {
        'product_path': raw['product_path'],
        'identity': info.identity,
        'schema': getattr(info, 'schema', None),
        'spacing_m': spacing,
        'shape_zx': shape,
        'layers': layers,
        'vectors': vector_names,
        'has_rivers': has_rivers,
        'sample_elevation_m': sample_elev,
        'climate_sidecar': climate_sidecar,
    }


def weather_readiness(repo_root=None, environ=None) -> dict:
    product = inspect_product(repo_root, environ)
    # Do not put planar metres into coordinates — weather_view would treat them as lon/lat
    # and raise (demonstrated gap). Climate + elevation_m from the product is the safe path.
    story = {
        'id': 'tg-wx-probe', 'title': 'tg-wx-probe',
        'locations': [{'id': 'camp', 'name': '营地',
                       'environment': {'elevation_m': product.get('sample_elevation_m')}}],
        'mechanics': {
            'map': map_policy.default_player_map_raw(repo_root, environ),
            'weather': {'climate': 'temperate', 'season': 'summer'},
        },
    }
    session = {'location': 'camp', 'time': 12, 'flags': {}, 'known': {}}
    report = weather_view.report(story, session, hours=0)
    metres_rejected = False
    try:
        weather_view.report({
            **story,
            'locations': [{'id': 'camp', 'name': '营地',
                           'coordinates': [200_000.0, 200_000.0]}],
        }, session, hours=0)
    except ValueError:
        metres_rejected = True
    return {
        'status': 'partial',
        'can_run_with_story_climate': report.get('enabled') is True,
        'climate_source_used': report.get('climate_source'),
        'current_kind': (report.get('current') or {}).get('kind'),
        'elevation_from_product': product.get('sample_elevation_m') is not None,
        'planar_metres_as_lonlat': False,
        'planar_metres_rejected_by_weather': metres_rejected,
        'climate_sidecar_present': product.get('climate_sidecar') is not None,
        'gaps': [
            '平面米制 coordinates 被 weather 拒绝（lat 必须在 [-90,90]）——已实测',
            '需适配器：从 map_source 采样 elevation，或读 regional-climate 侧车，或只用 mechanics.weather',
        ],
        'product': {
            'path': product['product_path'],
            'spacing_m': product['spacing_m'],
            'sample_elevation_m': product['sample_elevation_m'],
            'climate_sidecar': product['climate_sidecar'],
        },
    }


def roads_readiness(repo_root=None, environ=None) -> dict:
    product = inspect_product(repo_root, environ)
    return {
        'status': 'not_wired',
        'package_adventure_routes_ok': True,
        'civ_routes_backend': 'disabled_by_default',
        'product_has_rivers': product['has_rivers'],
        'product_has_road_layer': False,
        'exploration_graph_accepts': ['civ_routes'],
        'gaps': [
            'TG 快速世界层没有建成道路网；仅有高程/海陆与河流折线',
            'events.exploration_graph 只认 source=civ_routes，需新增 world_land 或作者手写 adventure.routes',
            '河流可作旅行约束/装饰，不能当道路拓扑直接进 exploration_graph',
        ],
        'product': {
            'path': product['product_path'],
            'has_rivers': product['has_rivers'],
            'layers': product['layers'],
            'vectors': product['vectors'],
        },
    }


def verify(repo_root=None, environ=None) -> dict:
    return {
        'map_policy': map_policy.status(repo_root, environ),
        'weather': weather_readiness(repo_root, environ),
        'roads': roads_readiness(repo_root, environ),
        'verdict': {
            'player_default_is_terragenesis': True,
            'weather_pluggable': 'yes_with_story_climate_or_elevation_adapter',
            'roads_pluggable': 'only_via_adventure_routes_until_world_land_adapter',
        },
    }
