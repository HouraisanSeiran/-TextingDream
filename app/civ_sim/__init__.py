# -*- coding: utf-8 -*-
"""Civilisation simulator: habitat, stepper, chronicle, history candidate.

The terrain bed is an input. This package does not import civ-atlas and does
not vendor it. See ``docs/civ-sim.md``.
"""
from .catalog import LoreCatalog, NameCatalog, load_lore_catalog, load_name_catalog
from .config import CivSimConfig
from .engine import simulate
from .errors import CivSimError
from .geography import Habitat, Region, habitat_from_arrays, habitat_from_source
from .history_bridge import load_chronicle_run, to_history_candidate
from .run import run_product
from .schema import ALGORITHM, LICENSE_NOTE

__all__ = [
    "ALGORITHM",
    "CivSimConfig",
    "CivSimError",
    "Habitat",
    "LICENSE_NOTE",
    "LoreCatalog",
    "NameCatalog",
    "Region",
    "habitat_from_arrays",
    "habitat_from_source",
    "load_chronicle_run",
    "load_lore_catalog",
    "load_name_catalog",
    "run_product",
    "simulate",
    "to_history_candidate",
]
