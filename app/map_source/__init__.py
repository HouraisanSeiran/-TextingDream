"""Unified frozen world-map sources. Consumers import this package, not adapters."""
from .types import (
    SourceInfo, MapSource, MapSourceError, MissingLayerError, UnsupportedSourceError,
    STANDARD_LAYERS, DEFAULT_LAYERS, UNPREPARED, OUT_OF_BOUNDS, UNKNOWN,
    OCEAN, CLOSED_BELOW_SEA, LAND, STATUS_NAMES,
)
from .registry import SUPPORTED_SCHEMAS, register_adapter, load_source
from .catalog import MapCatalog, load_catalog, load_default_catalog

__all__ = [
    "SourceInfo", "MapSource", "MapSourceError", "MissingLayerError", "UnsupportedSourceError",
    "STANDARD_LAYERS", "DEFAULT_LAYERS", "UNPREPARED", "OUT_OF_BOUNDS", "UNKNOWN", "OCEAN",
    "CLOSED_BELOW_SEA", "LAND", "STATUS_NAMES", "SUPPORTED_SCHEMAS", "register_adapter",
    "load_source", "MapCatalog", "load_catalog", "load_default_catalog",
]
