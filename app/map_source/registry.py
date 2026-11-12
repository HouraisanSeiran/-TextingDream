"""Explicit adapter registration and schema dispatch, with no guessing."""
from pathlib import Path
import numpy as np

from app import terrain_source as ts
from . import adapters
from .types import UnsupportedSourceError

_REGISTRY = {}
SUPPORTED_SCHEMAS = {
    "native-terrain-v3": ("new-world-terrain-v3",),
    "tectonic-macro-v2": ("tectonic-frozen-product-v2", "tectonic-frozen-product-v1"),
    "world-relief-pilot": ("world-relief-pilot-1.0", "world-relief-pilot-2.0"),
    "world-map-product": ("world-map-product-v1", "td-world-960m-v1", "td-world-960m-v2", "td-world-960m-v3", "td-world-960m-v4", "td-world-960m-v5", "td-world-960m-v6", "terragenesis-fast-relief-v1"),
    "terragenesis-regional-climate": ("terragenesis-regional-climate-v1",),
}


def register_adapter(kind, schema, loader):
    ts._require(isinstance(kind, str) and isinstance(schema, str) and callable(loader), "Invalid adapter registration")
    ts._require((kind, schema) not in _REGISTRY, f"Adapter already registered: {(kind, schema)!r}")
    _REGISTRY[kind, schema] = loader
    SUPPORTED_SCHEMAS[kind] = tuple(dict.fromkeys((*SUPPORTED_SCHEMAS.get(kind, ()), schema)))


for _kind, _loader in (("native-terrain-v3", adapters.load_native), ("tectonic-macro-v2", adapters.load_tectonic),
                       ("world-relief-pilot", adapters.load_relief), ("world-map-product", adapters.load_world_map)):
    for _schema in SUPPORTED_SCHEMAS[_kind]:
        register_adapter(_kind, _schema, adapters.load_td_world if _schema in ("td-world-960m-v1", "td-world-960m-v2", "td-world-960m-v3", "td-world-960m-v4", "td-world-960m-v5", "td-world-960m-v6", "terragenesis-fast-relief-v1") else _loader)

register_adapter(adapters.LOCAL30_KIND, adapters.LOCAL30_SCHEMA, adapters.load_local30)
register_adapter(adapters.CLIMATE_KIND, adapters.CLIMATE_SCHEMA, adapters.load_regional_climate)

# The frozen atlas renderer asks for kind "world-relief-pilot" (same arrays + rivers). This alias lets it read the TD
# world product through the unified interface without touching atlas.py. It is deliberately NOT listed in
# SUPPORTED_SCHEMAS (the product's own kind is world-map-product) and the loaded source still reports that kind.
_REGISTRY["world-relief-pilot", "td-world-960m-v1"] = adapters.load_td_world
_REGISTRY["world-relief-pilot", "td-world-960m-v2"] = adapters.load_td_world
_REGISTRY["world-relief-pilot", "td-world-960m-v3"] = adapters.load_td_world
_REGISTRY["world-relief-pilot", "td-world-960m-v4"] = adapters.load_td_world
_REGISTRY["world-relief-pilot", "td-world-960m-v5"] = adapters.load_td_world
_REGISTRY["world-relief-pilot", "td-world-960m-v6"] = adapters.load_td_world
_REGISTRY["world-relief-pilot", "terragenesis-fast-relief-v1"] = adapters.load_td_world


def load_source(kind, path, *, expected_identity=None, expected_world_seed=None):
    try:
        path = Path(path)
        if path.is_dir():
            manifest = ts._json((path / "manifest.json").read_text(encoding="utf-8"))
        else:
            with np.load(path, allow_pickle=False) as archive:
                raw = archive["manifest_json"]
                ts._require(raw.shape == () and raw.dtype.kind == "U", "Invalid manifest_json")
                manifest = ts._json(raw.item())
        schema = manifest.get("schema")
        if not isinstance(schema, str) or (kind, schema) not in _REGISTRY:
            raise UnsupportedSourceError(f"Unsupported map source kind={kind!r}, schema={schema!r}")
        source = _REGISTRY[kind, schema](path, expected_identity=expected_identity)
        if expected_world_seed is not None:
            ts._require(type(expected_world_seed) is int and source.info.world_seed == expected_world_seed, "Expected world_seed mismatch")
        return source
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, OverflowError) as exc:
        if isinstance(exc, ts.TerrainSourceError):
            raise
        raise ts.TerrainSourceError(f"Invalid map source kind={kind!r}: {exc}") from exc
