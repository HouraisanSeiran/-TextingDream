"""Fine-first source selection; a selected source owns every requested layer."""
import os
from pathlib import Path

import numpy as np

from app import terrain_source as ts
from .registry import load_source
from .types import DEFAULT_LAYERS, STANDARD_LAYERS, MissingLayerError


class MapCatalog:
    def __init__(self, sources=()):
        self.sources = tuple(sorted(sources, key=lambda source: source.info.spacing_m))
        self.products = self.sources

    def provenance(self):
        return [source.provenance() for source in self.sources]

    def sample(self, x_m, z_m, layers=DEFAULT_LAYERS):
        layers = (layers,) if isinstance(layers, str) else tuple(layers)
        for name in layers:
            if name not in STANDARD_LAYERS:
                raise MissingLayerError(f"Unknown standard layer: {name!r}")
        x, z = ts._coordinates(x_m, z_m)
        result = {name: np.full(x.shape, ts.UNPREPARED, dtype=np.uint8) if name == "status" else np.full(x.shape, np.nan) for name in layers}
        identities = np.full(x.shape, None, dtype=object)
        infos = np.full(x.shape, None, dtype=object)
        for source in self.sources:
            x0, z0, x1, z1 = source.info.extent_m
            selected = (identities == None) & (x >= x0) & (x <= x1) & (z >= z0) & (z <= z1)
            if not np.any(selected):
                continue
            sampled = source.sample(x[selected], z[selected], layers)
            for name in layers:
                result[name][selected] = sampled[name]
            identities[selected] = source.info.identity
            for position in np.flatnonzero(selected):
                infos.flat[position] = source.info
        result.update(source=identities, source_info=infos)
        for value in result.values():
            value.flags.writeable = False
        return result

    @classmethod
    def from_config(cls, config_path):
        return load_catalog(config_path)

    @classmethod
    def from_environment(cls):
        return load_default_catalog()


def load_catalog(config_path):
    try:
        path = Path(config_path)
        config = ts._json(path.read_text(encoding="utf-8"))
        ts._require(isinstance(config["sources"], list), "sources must be a list")
        sources = []
        for entry in config["sources"]:
            ts._require(ts._hex(entry.get("identity")), "Source identity is required")
            ts._require(isinstance(entry["path"], str), "Source path must be a string")
            if "expected_world_seed" in entry:
                ts._require(type(entry["expected_world_seed"]) is int, "expected_world_seed must be an integer")
            source_path = Path(entry["path"])
            if not source_path.is_absolute():
                source_path = path.parent / source_path
            sources.append(load_source(entry["kind"], source_path, expected_identity=entry["identity"], expected_world_seed=entry.get("expected_world_seed")))
        return MapCatalog(sources)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        if isinstance(exc, ts.TerrainSourceError):
            raise
        raise ts.TerrainSourceError(f"Invalid map catalog: {exc}") from exc


def load_default_catalog():
    path = os.environ.get("DREAM_TERRAIN_SOURCES")
    return load_catalog(path) if path else MapCatalog()
