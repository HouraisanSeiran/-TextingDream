# -*- coding: utf-8 -*-
"""Chronicle → author history document (store-compatible shape).

``WorldHistoryService.preview_civ_sim`` writes a ``history_preview`` from this
document. It is **not** a civ-atlas background: ``kind`` stays
``zhimeng_civ_sim_history_candidate``, and adoption uses a separate snapshot kind.
"""
import json
from pathlib import Path

from .chronicle import chronicle_sha256
from .errors import CivSimError
from .schema import CANDIDATE_KIND, CHRONICLE_SCHEMA, LICENSE_NOTE

_WINDOW_YEARS = 150
_EXACT = "exact"
_INTERVAL = "as_of_interval"
_UNKNOWN = "unknown"


def load_chronicle_run(run_dir):
    """Load ``manifest.json`` + ``chronicle.json`` from a civ-sim output directory."""
    root = Path(run_dir).resolve()
    chronicle_path = root / "chronicle.json"
    manifest_path = root / "manifest.json"
    if not chronicle_path.is_file() or not manifest_path.is_file():
        raise CivSimError("文明模拟目录需要 manifest.json 与 chronicle.json：%s" % root)
    chronicle = json.loads(chronicle_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if chronicle.get("schema") != CHRONICLE_SCHEMA:
        raise CivSimError("编年史 schema 不对")
    digest = chronicle_sha256(chronicle)
    pinned = manifest.get("chronicle_sha256")
    if pinned and pinned != digest:
        raise CivSimError("manifest 的 chronicle_sha256 与编年史内容不符")
    return {"root": root, "chronicle": chronicle, "manifest": manifest, "digest": digest}


def to_history_candidate(
    chronicle,
    *,
    base_year=None,
    window_years=_WINDOW_YEARS,
    branch=None,
    max_events=None,
    max_entities=None,
    chronicle_digest=None,
    run_id=None,
):
    """Bounded author-side document for one base year (store paging shape)."""
    if not isinstance(chronicle, dict) or chronicle.get("schema") != CHRONICLE_SCHEMA:
        raise CivSimError("需要一份文明模拟编年史")
    if type(window_years) is not int or window_years < 0:
        raise CivSimError("window_years 必须是非负整数")
    start = chronicle["start_year"]
    end = chronicle["end_year"]
    year = end if base_year is None else base_year
    if type(year) is not int:
        raise CivSimError("base_year 必须是整数")
    if year < start or year > end:
        raise CivSimError("基准年 %d 不在这次推演的 %d…%d 之内" % (year, start, end))
    if max_events is not None and (type(max_events) is not int or max_events <= 0):
        raise CivSimError("max_events 必须是正整数")
    if max_entities is not None and (type(max_entities) is not int or max_entities <= 0):
        raise CivSimError("max_entities 必须是正整数")

    window_from = max(start, year - window_years)
    snap = None
    for row in chronicle["snapshots"]:
        if row["year"] == year:
            snap = row
            break
    if snap is None:
        raise CivSimError("编年史没有基准年的政体快照")

    digest = chronicle_digest or chronicle_sha256(chronicle)
    branch_name = branch or "main"
    prefix = "civsim:%s:%s" % (chronicle["map_identity"][:16], chronicle["seed"])
    run_key = run_id or ("cs_" + digest[:12])

    events = []
    inside = 0
    truncated_events = False
    for index, event in enumerate(chronicle["annals"]):
        if not window_from <= event["year"] <= year:
            continue
        inside += 1
        if max_events is not None and len(events) >= max_events:
            truncated_events = True
            continue
        polity_a = event["polity_a"]
        polity_b = event["polity_b"]
        events.append({
            "ref": "%s/annal/%d" % (prefix, index),
            "year": event["year"],
            "kind": event["kind"],
            "a_ref": None if polity_a is None else "%s/polity/%d" % (prefix, polity_a),
            "b_ref": None if polity_b is None else "%s/polity/%d" % (prefix, polity_b),
            "region": event["region"],
            "settlement_ref": None,
            "road_version": event["road_version"],
            "note": event["note"],
            "provenance": "zhimeng_civ_sim",
        })

    polities = []
    settlements = []
    truncated_entities = False
    for row in snap["polities"]:
        if not row["alive"]:
            continue
        if max_entities is not None and len(polities) >= max_entities:
            truncated_entities = True
            continue
        pref = "%s/polity/%d" % (prefix, row["id"])
        polities.append({
            "ref": pref,
            "id": row["id"],
            "display_name": row["name"],
            "founded": row["founded"],
            "capital_region": row["capital"],
            "regions": list(row["regions"]),
            "at_war": list(row["at_war"]),
            "dynasty_ref": None if row.get("dynasty_id") is None else "%s/dynasty/%d" % (prefix, row["dynasty_id"]),
            "faith_ref": None if not row.get("faith_id") else "%s/faith/%s" % (prefix, row["faith_id"]),
            "monarch_ref": None if row.get("monarch_id") is None else "%s/person/%d" % (prefix, row["monarch_id"]),
        })
        settlements.append({
            "ref": "%s/settlement/%d" % (prefix, row["id"]),
            "display_name": "%s都" % row["name"],
            "founded": row["founded"],
            "region": row["capital"],
            "location_id": None,
            "polity_ref": pref,
            "note": "州府代理；尚未接城镇四阶段",
        })

    people = []
    for row in snap.get("people") or ():
        if max_entities is not None and len(people) >= max_entities:
            truncated_entities = True
            break
        people.append({
            "ref": "%s/person/%d" % (prefix, row["id"]),
            "display_name": row["name"],
            "role": row.get("role"),
            "title": row.get("title"),
            "polity_ref": "%s/polity/%d" % (prefix, row["polity_id"]),
            "dynasty_ref": None if row.get("dynasty_id") is None else "%s/dynasty/%d" % (prefix, row["dynasty_id"]),
            "born": row.get("born"),
            "from_year": row.get("from_year"),
        })

    dynasties = []
    for row in snap.get("dynasties") or ():
        if row.get("ended") is not None and row["ended"] < year:
            continue
        dynasties.append({
            "ref": "%s/dynasty/%d" % (prefix, row["id"]),
            "display_name": row["name"],
            "founded": row["founded"],
            "polity_ref": "%s/polity/%d" % (prefix, row["polity_id"]),
            "faith_ref": None if not row.get("faith_id") else "%s/faith/%s" % (prefix, row["faith_id"]),
        })

    religion_items = []
    # An explicitly empty old-year snapshot means no faith was adopted yet. It
    # must not fall through to faiths introduced in the completed run's future.
    faith_rows = snap.get("faiths")
    if faith_rows is None:
        faith_rows = chronicle.get("faiths") or ()
    for row in faith_rows:
        if row.get("adopted_year") is not None and row["adopted_year"] > year:
            continue
        religion_items.append({
            "ref": "%s/faith/%s" % (prefix, row["id"]),
            "display_name": row["name"],
            "founded": row.get("adopted_year"),
            "element_ref": row.get("element_ref"),
            "note": "百科候选信仰名；不等于神迹真实",
        })

    provenance = chronicle.get("provenance") or {}
    field_status = {
        "annals": {"status": _EXACT, "note": "编年事件带明确年份"},
        "polity_founded": {"status": _EXACT, "note": "政体 founded 字段"},
        "region_polity": {"status": _INTERVAL, "note": "仅年末快照，无逐格变更日志"},
        "region_culture": {"status": _UNKNOWN, "note": "无独立文化层；国祀见 religion"},
        "settlement_lifespan": {"status": _INTERVAL, "note": "仅首都代理点"},
        "settlement_capital_spans": {"status": _UNKNOWN, "note": "不迁都"},
        "polity_capital_spans": {"status": _UNKNOWN, "note": "不迁都"},
        "people_lifespan": {"status": _INTERVAL, "note": "人物有 born/from/died；无完整家谱树"},
        "religion_events": {"status": _EXACT, "note": "faith_adopt / convert 记入国祀更替"},
        "population": {"status": _UNKNOWN, "note": "无逐年人口"},
        "resources": {"status": _UNKNOWN, "note": "无资源层"},
        "routes": {"status": _INTERVAL, "note": "道路为占邻州边；用 road_version"},
        "terrain": {"status": _UNKNOWN, "note": "床面来自冻结 world_map_product，本模块不改"},
    }
    return {
        "schema": 1,
        "kind": CANDIDATE_KIND,
        "for_author_review": True,
        "auto_canonical": False,
        "store_bridge": {
            "status": "preview_ready",
            "preview_written": False,
            "adoption": "via_world_history_store.preview_civ_sim",
            "source_kind": "civ_sim",
        },
        "identity": {
            "content_sha256": digest,
            "import_id": run_key,
            "branch": branch_name,
            "civ_seed": chronicle["seed"],
            "civ_seed_source": "civ_sim.config.seed",
            "map_identity": chronicle["map_identity"],
            "world_id": chronicle["map_identity"][:16],
            "generator": provenance.get("algorithm"),
            "snapshot_format": None,
        },
        "provenance": {
            "producer": "app/civ_sim",
            "reader": "app/civ_sim/history_bridge.py",
            "algorithm": provenance.get("algorithm"),
            "map_identity": chronicle["map_identity"],
            "map_kind": provenance.get("map_kind"),
            "world_seed": provenance.get("world_seed"),
            "civ_seed": chronicle["seed"],
            "road_version": snap["road_version"],
            "name_catalog": provenance.get("name_catalog"),
            "upstream_code_copied": False,
            "license_note": LICENSE_NOTE,
            "spec_commit": None,
        },
        "selection": {
            "base_year": year,
            "end_year": end,
            "window": {"from": window_from, "to": year},
            "window_years": year - window_from,
            "max_events": max_events,
            "max_entities": max_entities,
            "hidden_refs": [],
        },
        "terrain": {
            "status": "external_world_map_product",
            "map_identity": chronicle["map_identity"],
            "note": "地形由 Terragenesis/fast 产品提供；历史层不携带床面数组",
            "eras_block": False,
        },
        "field_status": field_status,
        "unknown": [
            {"field": key, "reason": row["note"]}
            for key, row in field_status.items() if row["status"] == _UNKNOWN
        ],
        "annals": {
            "events": events,
            "counts": {
                "inside_window": inside,
                "returned": len(events),
                "truncated": truncated_events,
            },
        },
        "polities": {
            "items": polities,
            "alive_at_base_year": len(polities) + (1 if truncated_entities else 0),
            "returned": len(polities),
            "truncated": truncated_entities,
        },
        "settlements": {
            "items": settlements,
            "alive_at_base_year": len(settlements),
            "returned": len(settlements),
            "note": "首都代理；尚未接 towns.py",
        },
        "people": {
            "items": people,
            "alive_at_base_year": len(people),
            "returned": len(people),
            "available": True,
            "note": "君主/储君/廷臣；非完整家谱",
        },
        "dynasties": {
            "items": dynasties,
            "alive_at_base_year": len(dynasties),
            "returned": len(dynasties),
        },
        "religion": {
            "items": religion_items,
            "alive_at_base_year": len(religion_items),
            "returned": len(religion_items),
            "note": "国祀候选名来自百科 religions / 内置回退；不宣称神迹",
        },
        "not_simulated": ["full_genealogy", "sect_schism_tree", "town_layout", "route_capacity"],
    }
