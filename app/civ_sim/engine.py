# -*- coding: utf-8 -*-
"""Deterministic polity stepper.

Same civilisation seed and the same habitat produce the same chronicle.
Provinces are the habitat's land blocks. Roads are undirected edges added
when a polity takes a neighbouring block; ``road_version`` is the edge count.
"""
from collections import deque

from .catalog import LoreCatalog
from .chronicle import finalize
from .config import CivSimConfig
from .errors import CivSimError
from .schema import ALGORITHM, CHRONICLE_SCHEMA, LICENSE_NOTE
from .society import SocietyState

_MASK = (1 << 64) - 1
_PREFIXES = (
    "青", "澜", "石", "禾", "浦", "岑", "汐", "梧",
    "棠", "洛", "榆", "柏", "沙", "澄", "苇", "岬",
    "岚", "茗", "柘", "淇", "矾", "柿", "枳", "楝",
    "槐", "栎", "柠", "橘", "桐", "槿", "萝", "葵",
)
_SUFFIXES = (
    "津", "原", "港", "岭", "泽", "川", "坞", "渡",
    "丘", "湾", "滩", "谷", "坪", "洲", "埠", "关",
    "甸", "陂", "溪", "冈", "屿", "淀", "阜", "隰",
    "汭", "湄", "沚", "漪", "濑", "浔", "汀", "浦",
)


class _Stream:
    """SplitMix64. The draw order is part of the result."""

    def __init__(self, seed):
        self.state = ((seed & _MASK) + 0x9E3779B97F4A7C15) & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return (z ^ (z >> 31)) & _MASK

    def below(self, bound):
        return self.next() % bound


def _mix(*parts):
    value = 0x9E3779B97F4A7C15
    for part in parts:
        value ^= part & _MASK
        value = (value * 0xBF58476D1CE4E5B9) & _MASK
        value ^= value >> 30
        value = (value * 0x94D049BB133111EB) & _MASK
        value ^= value >> 27
    return value


def _suitability(region, config):
    climate = 0 if region.climate_millis is None else config.climate_weight * region.climate_millis
    return (
        config.river_weight * region.river_millis
        + config.coast_weight * region.coast_millis
        + climate
        - config.slope_weight * region.slope_millis
        - config.highland_weight * region.band
    )


def _name(seed, polity_id):
    token = _mix(seed, polity_id, 11)
    return _PREFIXES[token % 32] + _SUFFIXES[(token >> 8) % 32]


def _catalog_name(catalog, seed, polity_id):
    """Prefer encyclopedia tokens when a catalog was supplied; else built-in syllables."""
    tokens = getattr(catalog, "tokens", None) or ()
    if not tokens:
        return _name(seed, polity_id)
    n = len(tokens)
    left = tokens[_mix(seed, polity_id, 11) % n]
    right = tokens[_mix(seed, polity_id, 29) % n]
    if left == right:
        return left + "邦"
    return left + right


def _hops(neighbors, roots, allowed):
    allowed = set(allowed)
    dist = {}
    queue = deque()
    for root in roots:
        if root in allowed and root not in dist:
            dist[root] = 0
            queue.append(root)
    while queue:
        current = queue.popleft()
        for nxt in neighbors[current]:
            if nxt in allowed and nxt not in dist:
                dist[nxt] = dist[current] + 1
                queue.append(nxt)
    return dist


def _nearest(neighbors, capitals, count):
    if not capitals:
        return {}
    dist = _hops(neighbors, capitals, range(count))
    return dist


def simulate(habitat, config, catalog=None, lore=None):
    """Step ``config.start_year`` … ``config.end_year`` on one habitat.

    ``catalog`` is an optional :class:`NameCatalog` (polity display names).
    ``lore`` is an optional :class:`LoreCatalog` (dynasty / people / faiths).
    Geography and event timing stay on the civilisation seed.
    """
    if not isinstance(config, CivSimConfig):
        raise CivSimError("config 必须是 CivSimConfig")
    regions = habitat.regions
    neighbors = habitat.neighbors
    count = len(regions)
    owner = [-1] * count
    polities = []
    wars = {}
    roads = set()
    annals = []
    truncated = False
    stream = _Stream(config.seed)
    suit = [_suitability(region, config) for region in regions]
    society = None
    if config.society:
        society = SocietyState(lore if lore is not None else LoreCatalog(), config.seed, config)

    def version():
        return len(roads)

    def emit(year, kind, polity_a, polity_b, region, note):
        nonlocal truncated
        if len(annals) >= config.max_annals:
            truncated = True
            return
        annals.append({
            "year": int(year),
            "kind": kind,
            "polity_a": int(polity_a),
            "polity_b": None if polity_b is None else int(polity_b),
            "region": None if region is None else int(region),
            "road_version": version(),
            "note": note,
        })

    def owned(pid):
        return [index for index, holder in enumerate(owner) if holder == pid]

    def alive():
        return [row["id"] for row in polities if row["ended"] is None]

    def shares(left, right):
        for index, nbrs in enumerate(neighbors):
            if owner[index] != left:
                continue
            if any(owner[other] == right for other in nbrs):
                return True
        return False

    def border_region(left, right):
        found = []
        for index, nbrs in enumerate(neighbors):
            if owner[index] == left and any(owner[other] == right for other in nbrs):
                found.append(index)
        return min(found) if found else None

    def link(left, right):
        if left == right:
            return
        edge = (left, right) if left < right else (right, left)
        roads.add(edge)

    def found(year):
        if len(alive()) >= config.max_polities:
            return
        if (year - config.start_year) % config.found_period != 0:
            return
        for _ in range(config.max_founds_per_year):
            if len(alive()) >= config.max_polities:
                return
            capitals = [row["capital"] for row in polities if row["ended"] is None]
            dist = _nearest(neighbors, capitals, count)
            best = None
            for region in regions:
                if owner[region.id] != -1:
                    continue
                if capitals:
                    hops = dist.get(region.id, 10**9)
                    if hops < config.min_capital_hops:
                        continue
                jitter = _mix(config.seed, year, region.id, 3) % (config.found_jitter + 1)
                score = suit[region.id] * 1000 + jitter
                key = (score, -region.id)
                if best is None or key > best[0]:
                    best = (key, region.id)
            if best is None:
                return
            region_id = best[1]
            polity_id = len(polities)
            owner[region_id] = polity_id
            polities.append({
                "id": polity_id,
                "name": _catalog_name(catalog, config.seed, polity_id),
                "founded": year,
                "ended": None,
                "capital": region_id,
            })
            emit(year, "found", polity_id, None, region_id, "立国于州 %d" % region_id)
            if society is not None:
                society.on_found(year, polity_id, emit)

    def expand(year):
        for polity in polities:
            if polity["ended"] is not None:
                continue
            pid = polity["id"]
            held = owned(pid)
            if not held:
                continue
            roots = [polity["capital"]] if polity["capital"] in held else held
            dist = _hops(neighbors, roots, held)
            best = None
            for index, nbrs in enumerate(neighbors):
                if owner[index] != -1:
                    continue
                vias = [via for via in nbrs if owner[via] == pid and via in dist]
                if not vias:
                    continue
                hops = min(dist[via] for via in vias) + 1
                via = min(vias)
                region = regions[index]
                climate = 0 if region.climate_millis is None else config.climate_weight * region.climate_millis
                cost = (
                    config.base_expand_cost
                    + config.slope_weight * region.slope_millis
                    + config.highland_weight * region.band
                    + config.distance_weight * hops
                    - config.river_weight * region.river_millis
                    - config.coast_weight * region.coast_millis
                    - climate
                )
                key = (cost, index)
                if best is None or key < best[0]:
                    best = (key, index, via)
            if best is None or best[0][0] > config.expand_budget:
                continue
            region_id, via = best[1], best[2]
            owner[region_id] = pid
            link(via, region_id)
            emit(year, "expand", pid, None, region_id, "并入邻州 %d" % region_id)

    def declare(year):
        living = alive()
        candidates = []
        for pos, left in enumerate(living):
            for right in living[pos + 1:]:
                pair = (left, right) if left < right else (right, left)
                if pair in wars or not shares(pair[0], pair[1]):
                    continue
                candidates.append(pair)
        opened = 0
        for pair in sorted(candidates):
            if opened >= config.max_new_wars_per_year:
                break
            if stream.below(1000) >= config.war_per_mille:
                continue
            wars[pair] = year
            opened += 1
            emit(year, "war", pair[0], pair[1], border_region(pair[0], pair[1]), "开战")

    def contest(year):
        for pair in sorted(list(wars)):
            if pair not in wars:
                continue
            left, right = pair
            if polities[left]["ended"] is not None or polities[right]["ended"] is not None:
                wars.pop(pair, None)
                continue
            left_n = len(owned(left))
            right_n = len(owned(right))
            if left_n > right_n or (left_n == right_n and left < right):
                attacker, defender = left, right
            else:
                attacker, defender = right, left
            targets = []
            for index, nbrs in enumerate(neighbors):
                if owner[index] == defender and any(owner[other] == attacker for other in nbrs):
                    targets.append(index)
            if not targets:
                emit(year, "peace", left, right, None, "失去共同边界，休战")
                wars.pop(pair, None)
                continue
            target = max(targets, key=lambda index: (suit[index], -index))
            if stream.below(1000) < config.conquer_per_mille:
                vias = [via for via in neighbors[target] if owner[via] == attacker]
                owner[target] = attacker
                if vias:
                    link(min(vias), target)
                emit(year, "expand", attacker, defender, target, "战时夺得邻州 %d" % target)
                if not owned(defender):
                    polities[defender]["ended"] = year
                    emit(year, "fall", defender, attacker, target, "灭亡")
                    if society is not None:
                        society.on_fall(year, defender, emit)
                    for old in list(wars):
                        if defender in old:
                            wars.pop(old, None)
                    continue
            if pair not in wars:
                continue
            duration = year - wars[pair]
            if duration >= config.max_war_years or stream.below(1000) < config.peace_per_mille:
                emit(year, "peace", left, right, border_region(left, right), "休战")
                wars.pop(pair, None)

    def snapshot(year):
        rows = []
        for polity in polities:
            pid = polity["id"]
            at_war = sorted({other for pair in wars if pid in pair for other in pair if other != pid})
            row = {
                "id": pid,
                "name": polity["name"],
                "alive": polity["ended"] is None,
                "founded": polity["founded"],
                "ended": polity["ended"],
                "capital": polity["capital"],
                "regions": owned(pid),
                "at_war": at_war,
            }
            if society is not None:
                row["dynasty_id"] = society.polity_dynasty.get(pid)
                row["faith_id"] = society.polity_faith.get(pid)
                row["monarch_id"] = society.polity_monarch.get(pid)
            rows.append(row)
        payload = {"year": year, "road_version": version(), "polities": rows}
        if society is not None:
            living = [p["id"] for p in polities if p["ended"] is None]
            payload.update(society.snapshot_extras(set(living)))
        return payload

    snapshots = []
    for year in range(config.start_year, config.end_year + 1):
        if count:
            found(year)
            expand(year)
            declare(year)
            contest(year)
            if society is not None:
                society.yearly(year, alive(), stream, emit)
        snapshots.append(snapshot(year))

    document = {
        "schema": CHRONICLE_SCHEMA,
        "algorithm": ALGORITHM,
        "seed": config.seed,
        "start_year": config.start_year,
        "end_year": config.end_year,
        "truncated": truncated,
        "max_annals": config.max_annals,
        "provenance": {
            "producer": "app/civ_sim",
            "algorithm": ALGORITHM,
            "map_identity": habitat.map_identity,
            "map_kind": habitat.map_kind,
            "map_schema": habitat.map_schema,
            "world_seed": habitat.world_seed,
            "upstream_repo": "https://github.com/guaner-334/civ-atlas",
            "upstream_code_copied": False,
            "license_note": LICENSE_NOTE,
            "name_catalog": None if catalog is None else catalog.to_dict(),
            "lore_catalog": None if society is None else society.lore.to_dict(),
            "society": bool(society),
        },
        "map_identity": habitat.map_identity,
        "habitat": {
            "schema": habitat.schema,
            "region_count": count,
            "habitable_cells": habitat.habitable_cells,
            "ocean_cells": habitat.ocean_cells,
            "climate": habitat.climate,
            "block_cells": habitat.block_cells,
        },
        "regions": [region.to_dict() for region in regions],
        "adjacency": [list(row) for row in neighbors],
        "annals": annals,
        "roads": [list(edge) for edge in sorted(roads)],
        "road_version_final": len(roads),
        "snapshots": snapshots,
        "polities": snapshots[-1]["polities"] if snapshots else [],
        "counts": {
            "annals": len(annals),
            "polities": len(polities),
            "regions": count,
            "roads": len(roads),
            "years": config.end_year - config.start_year + 1,
        },
    }
    if society is not None:
        tables = society.final_tables()
        document["dynasties"] = tables["dynasties"]
        document["people"] = tables["people"]
        document["faiths"] = tables["faiths"]
        document["counts"]["dynasties"] = len(tables["dynasties"])
        document["counts"]["people"] = len(tables["people"])
        document["counts"]["faiths"] = len(tables["faiths"])
    else:
        document["dynasties"] = []
        document["people"] = []
        document["faiths"] = []
    return finalize(document)
