# -*- coding: utf-8 -*-
"""Read-only lore tokens from the existing human-encyclopedia SQLite.

Covers personal-name syllables, dynasty-title styles, court roles, and faith
display names (from the religions namespace when present). Library rows are
candidates only. Missing databases fall back to built-in tables.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from .errors import CivSimError

DEFAULT_DB = Path("artifacts/human-encyclopedia/encyclopedia.sqlite3")
DEFAULT_NAME_NAMESPACES = ("names-asian", "names-european", "civ-given-names")
DEFAULT_DYNASTY_NAMESPACE = "civ-dynasty-styles"
DEFAULT_FAITH_NAMESPACE = "religions"
_TOKEN_SPLIT = re.compile(r"[,，、/;；|\s]+")
_SKIP_HINTS = ("不能代表", "不把", "不等于", "仅供", "示例", "注意", "未取得", "残片")

_FALLBACK_ERA = ("青", "澜", "石", "禾", "浦", "岑", "汐", "梧", "棠", "洛", "榆", "柏")
_FALLBACK_SUFFIX = ("朝", "氏")
_FALLBACK_HOUSE = ("北原", "东湾", "西岭", "南泽")
_FALLBACK_TITLE = ("王", "帝", "公")
_FALLBACK_GIVEN = ("明", "德", "安", "宁", "远", "清", "正", "和", "嘉", "永")
_FALLBACK_ROLE = ("君主", "储君", "宰相", "将军", "祭司")
_FALLBACK_FAITH = ("天道", "社稷", "海神", "山灵", "祖先祀")


@dataclass(frozen=True)
class NameCatalog:
    """Sorted unique tokens plus provenance for the run manifest."""

    tokens: tuple
    db_path: str
    namespaces: tuple
    pool_ids: tuple
    source: str = "human-encyclopedia"

    def to_dict(self):
        return {
            "source": self.source,
            "db_path": self.db_path,
            "namespaces": list(self.namespaces),
            "pool_ids": list(self.pool_ids),
            "token_count": len(self.tokens),
            "canon": False,
            "note": "候选姓名池；库里有 ≠ 世界正典",
        }


@dataclass(frozen=True)
class LoreCatalog:
    """Dynasty / person / faith pools used by the society stepper."""

    era_chars: tuple = _FALLBACK_ERA
    dynasty_suffixes: tuple = _FALLBACK_SUFFIX
    house_names: tuple = _FALLBACK_HOUSE
    titles: tuple = _FALLBACK_TITLE
    given_names: tuple = _FALLBACK_GIVEN
    roles: tuple = _FALLBACK_ROLE
    faiths: tuple = field(default_factory=lambda: tuple(
        {"id": "local_%d" % index, "name": name, "element_ref": None}
        for index, name in enumerate(_FALLBACK_FAITH)
    ))
    name_tokens: tuple = ()
    db_path: str | None = None
    pool_ids: tuple = ()
    source: str = "builtin-fallback"

    def to_dict(self):
        return {
            "source": self.source,
            "db_path": self.db_path,
            "pool_ids": list(self.pool_ids),
            "counts": {
                "era_chars": len(self.era_chars),
                "dynasty_suffixes": len(self.dynasty_suffixes),
                "house_names": len(self.house_names),
                "titles": len(self.titles),
                "given_names": len(self.given_names),
                "roles": len(self.roles),
                "faiths": len(self.faiths),
                "name_tokens": len(self.name_tokens),
            },
            "canon": False,
            "note": "候选文化素材；库里有 ≠ 世界正典 / 不等于教义真实",
        }


def _tokens_from_aliases(aliases):
    out = []
    if not aliases:
        return out
    for entry in aliases:
        if not isinstance(entry, str):
            continue
        text = entry.strip()
        if not text or any(hint in text for hint in _SKIP_HINTS):
            continue
        if _TOKEN_SPLIT.search(text):
            parts = [part.strip() for part in _TOKEN_SPLIT.split(text) if part.strip()]
        else:
            parts = [text]
        for part in parts:
            if any(hint in part for hint in _SKIP_HINTS):
                continue
            if 1 <= len(part) <= 16:
                out.append(part)
    return out


def _paged_items(enc, path, namespace):
    offset = 0
    while True:
        page = enc.search(path, namespace=namespace, limit=50, offset=offset, include_payload=False)
        for item in page.get("items") or ():
            yield item
        if not page.get("has_more"):
            return
        offset += int(page.get("returned") or 0)
        if offset <= 0:
            return


def load_name_catalog(db_path=None, *, namespaces=DEFAULT_NAME_NAMESPACES, required=False):
    """Load name tokens from ``encyclopedia`` search. Optional unless ``required``."""
    path = Path(DEFAULT_DB if db_path is None else db_path)
    namespaces = tuple(namespaces) if namespaces else DEFAULT_NAME_NAMESPACES
    if not path.is_file():
        if required:
            raise CivSimError("百科库不存在：%s" % path)
        return None
    try:
        from app import encyclopedia as enc
    except Exception as exc:
        if required:
            raise CivSimError("无法导入百科模块：%s" % exc) from exc
        return None
    tokens = []
    pool_ids = []
    try:
        for namespace in namespaces:
            for item in _paged_items(enc, path, namespace):
                pool_ids.append("%s/%s" % (item.get("namespace"), item.get("element_id")))
                tokens.extend(_tokens_from_aliases(item.get("aliases") or ()))
    except Exception as exc:
        if required:
            raise CivSimError("读取百科姓名池失败：%s" % exc) from exc
        return None
    unique = tuple(sorted(set(tokens)))
    if not unique:
        if required:
            raise CivSimError("百科姓名池为空：%s" % path)
        return None
    return NameCatalog(
        tokens=unique,
        db_path=str(path.resolve()),
        namespaces=namespaces,
        pool_ids=tuple(sorted(set(pool_ids))),
    )


def load_lore_catalog(db_path=None, *, required=False):
    """Load dynasty / given-name / faith pools. Always returns a catalog (builtin if needed)."""
    path = Path(DEFAULT_DB if db_path is None else db_path)
    if not path.is_file():
        if required:
            raise CivSimError("百科库不存在：%s" % path)
        return LoreCatalog()
    try:
        from app import encyclopedia as enc
    except Exception as exc:
        if required:
            raise CivSimError("无法导入百科模块：%s" % exc) from exc
        return LoreCatalog()

    era, suffix, house, titles, given, roles = [], [], [], [], [], []
    faiths = []
    pool_ids = []
    try:
        for item in _paged_items(enc, path, DEFAULT_DYNASTY_NAMESPACE):
            pool_ids.append("%s/%s" % (item.get("namespace"), item.get("element_id")))
            tokens = _tokens_from_aliases(item.get("aliases") or ())
            eid = item.get("element_id") or ""
            if "suffix" in eid:
                suffix.extend(tokens)
            elif "european" in eid or "house" in eid:
                house.extend(tokens)
            elif "title" in eid:
                titles.extend(tokens)
            else:
                era.extend(tokens)
        for item in _paged_items(enc, path, "civ-given-names"):
            pool_ids.append("%s/%s" % (item.get("namespace"), item.get("element_id")))
            tokens = _tokens_from_aliases(item.get("aliases") or ())
            eid = item.get("element_id") or ""
            if "role" in eid:
                roles.extend(tokens)
            else:
                given.extend(tokens)
        for item in _paged_items(enc, path, DEFAULT_FAITH_NAMESPACE):
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            if any(hint in name for hint in _SKIP_HINTS):
                continue
            # Prefer broad tradition over ritessingle-rite rows: keep entries tagged overview-ish
            tags = set(item.get("tags") or ())
            if tags & {"ritual", "festival", "scripture", "clergy"} and "tradition" not in tags:
                # still allow; simulator will sample among all named faiths
                pass
            faiths.append({
                "id": item.get("element_id") or name,
                "name": name.strip(),
                "element_ref": "%s/%s" % (item.get("namespace"), item.get("element_id")),
            })
            pool_ids.append("%s/%s" % (item.get("namespace"), item.get("element_id")))
        name_cat = load_name_catalog(path, required=False)
        name_tokens = name_cat.tokens if name_cat else ()
    except Exception as exc:
        if required:
            raise CivSimError("读取文明文化素材失败：%s" % exc) from exc
        return LoreCatalog()

    def uniq(seq, fallback):
        out = tuple(sorted(set(seq)))
        return out if out else fallback

    faith_rows = tuple(faiths) if faiths else LoreCatalog().faiths
    return LoreCatalog(
        era_chars=uniq(era, _FALLBACK_ERA),
        dynasty_suffixes=uniq(suffix, _FALLBACK_SUFFIX),
        house_names=uniq(house, _FALLBACK_HOUSE),
        titles=uniq(titles, _FALLBACK_TITLE),
        given_names=uniq(given, _FALLBACK_GIVEN),
        roles=uniq(roles, _FALLBACK_ROLE),
        faiths=faith_rows,
        name_tokens=name_tokens or (),
        db_path=str(path.resolve()),
        pool_ids=tuple(sorted(set(pool_ids))),
        source="human-encyclopedia",
    )
