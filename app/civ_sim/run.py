# -*- coding: utf-8 -*-
"""Read a frozen world-map product and write a civilisation run beside it.

The product directory is only opened for reading. Output goes to a separate
directory and never replaces elevation, status, or identity.
"""
import json
from pathlib import Path

from app.map_source import load_source

from .catalog import load_lore_catalog, load_name_catalog
from .chronicle import chronicle_json, chronicle_sha256
from .config import CivSimConfig
from .engine import simulate
from .errors import CivSimError
from .geography import habitat_from_source
from .schema import ALGORITHM, LICENSE_NOTE, RUN_SCHEMA


def run_product(product_path, *, identity, config, out_dir, encyclopedia_db=None,
                name_namespaces=None, require_catalog=False):
    """Load ``world-map-product``, simulate, write manifest.json and chronicle.json.

    ``encyclopedia_db`` points at the existing human-encyclopedia SQLite (optional).
    Names / dynasty styles / faiths are candidates only; the library is never written.
    """
    if not isinstance(config, CivSimConfig):
        raise CivSimError("config 必须是 CivSimConfig")
    if not isinstance(identity, str) or not identity:
        raise CivSimError("必须显式给出地图 identity")
    product = Path(product_path).resolve()
    out = Path(out_dir).resolve()
    if out == product or product in out.parents or out in product.parents:
        raise CivSimError("输出目录不能落在地形产品目录里面，也不能是产品的上级目录")
    if out.exists() and not out.is_dir():
        raise CivSimError("输出路径已是文件")
    source = load_source("world-map-product", product, expected_identity=identity)
    if source.info.identity != identity:
        raise CivSimError("读到的地图 identity 与参数不一致")
    habitat = habitat_from_source(
        source,
        block_cells=config.block_cells,
        min_land_cells=config.min_land_cells,
        river_radius_m=config.river_radius_m,
        coast_scale_m=config.coast_scale_m,
    )
    catalog = load_name_catalog(
        encyclopedia_db, namespaces=name_namespaces, required=require_catalog,
    )
    lore = load_lore_catalog(encyclopedia_db, required=require_catalog)
    chronicle = simulate(habitat, config, catalog=catalog, lore=lore)
    digest = chronicle_sha256(chronicle)
    manifest = {
        "schema": RUN_SCHEMA,
        "algorithm": ALGORITHM,
        "license_note": LICENSE_NOTE,
        "upstream_code_copied": False,
        "map": {
            "kind": source.info.kind,
            "schema": source.info.schema,
            "identity": source.info.identity,
            "world_seed": source.info.world_seed if type(source.info.world_seed) is int else None,
            "spacing_m": float(source.info.spacing_m),
            "shape_zx": [int(source.info.shape_zx[0]), int(source.info.shape_zx[1])],
            "producer": source.info.producer,
            "algorithm_version": source.info.algorithm_version,
        },
        "config": config.to_dict(),
        "name_catalog": None if catalog is None else catalog.to_dict(),
        "lore_catalog": lore.to_dict(),
        "habitat": chronicle["habitat"],
        "counts": chronicle["counts"],
        "chronicle_sha256": digest,
        "writes": ["manifest.json", "chronicle.json"],
        "terrain_modified": False,
    }
    out.mkdir(parents=True, exist_ok=True)
    chronicle_path = out / "chronicle.json"
    manifest_path = out / "manifest.json"
    chronicle_path.write_text(chronicle_json(chronicle), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "out_dir": str(out),
        "manifest_path": str(manifest_path),
        "chronicle_path": str(chronicle_path),
        "chronicle_sha256": digest,
        "map_identity": source.info.identity,
        "counts": chronicle["counts"],
    }
