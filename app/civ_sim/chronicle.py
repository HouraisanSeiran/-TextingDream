# -*- coding: utf-8 -*-
"""Chronicle document: bounded annals plus a polity snapshot at each year end."""
import hashlib
import json

from .errors import CivSimError
from .schema import ANNAL_KINDS, CHRONICLE_SCHEMA


def canonical_bytes(chronicle):
    return json.dumps(chronicle, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def chronicle_sha256(chronicle):
    return hashlib.sha256(canonical_bytes(chronicle)).hexdigest()


def chronicle_json(chronicle):
    """Pretty JSON for the artifact file. The manifest hash uses the compact form."""
    return json.dumps(chronicle, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def finalize(chronicle):
    """Check the invariants the tests pin, then return the same document."""
    if chronicle.get("schema") != CHRONICLE_SCHEMA:
        raise CivSimError("编年史 schema 不对")
    start = chronicle["start_year"]
    end = chronicle["end_year"]
    annals = chronicle["annals"]
    previous = start
    for index, event in enumerate(annals):
        if event["kind"] not in ANNAL_KINDS:
            raise CivSimError("不认识的事件种类：%s" % event["kind"])
        year = event["year"]
        if type(year) is not int or year < previous or year > end:
            raise CivSimError("编年史年份不是单调的（第 %d 条）" % index)
        previous = year
        if event["polity_a"] is None:
            raise CivSimError("事件缺少 polity_a")
    snaps = chronicle["snapshots"]
    expected = list(range(start, end + 1))
    if [row["year"] for row in snaps] != expected:
        raise CivSimError("缺了某一年的政体快照")
    if chronicle["road_version_final"] != len(chronicle["roads"]):
        raise CivSimError("道路图版本与边数不一致")
    return chronicle
