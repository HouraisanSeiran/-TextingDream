# -*- coding: utf-8 -*-
"""Dynasty, people and state-faith layer on top of polity ownership.

Deterministic: same seed + lore catalog + polity events → same society rows.
Does not assert that encyclopedia faiths are theologically true in-world.
"""
from .catalog import LoreCatalog

_MASK = (1 << 64) - 1


def _mix(*parts):
    value = 0x9E3779B97F4A7C15
    for part in parts:
        value ^= part & _MASK
        value = (value * 0xBF58476D1CE4E5B9) & _MASK
        value ^= value >> 30
        value = (value * 0x94D049BB133111EB) & _MASK
        value ^= value >> 27
    return value


def _pick(seq, *parts):
    if not seq:
        return None
    return seq[_mix(*parts) % len(seq)]


def _person_name(lore, seed, person_id):
    tokens = lore.name_tokens or lore.given_names
    if not tokens:
        tokens = lore.given_names
    left = _pick(tokens, seed, person_id, 41)
    right = _pick(lore.given_names, seed, person_id, 43)
    if left == right:
        return left
    # Prefer short sinitic-style compounds when both sides are short.
    if len(left) <= 2 and len(right) <= 2:
        return left + right
    return left if len(left) >= 2 else (left + right)


def _dynasty_name(lore, seed, dynasty_id, style_bit):
    if style_bit % 2 == 0:
        era = _pick(lore.era_chars, seed, dynasty_id, 51)
        suffix = _pick(lore.dynasty_suffixes, seed, dynasty_id, 53)
        return era + suffix
    house = _pick(lore.house_names, seed, dynasty_id, 55)
    return house + "王朝"


def _title(lore, seed, person_id):
    return _pick(lore.titles, seed, person_id, 57) or "王"


def _role(lore, key):
    roles = lore.roles or ()
    for name in roles:
        if key in name:
            return name
    mapping = {"monarch": "君主", "heir": "储君", "minister": "宰相",
               "general": "将军", "cleric": "祭司"}
    return mapping.get(key, key)


class SocietyState:
    """Mutable society tables for one simulate() run."""

    def __init__(self, lore, seed, config):
        self.lore = lore if isinstance(lore, LoreCatalog) else LoreCatalog()
        self.seed = seed
        self.config = config
        self.dynasties = []
        self.people = []
        self.faiths_used = {}  # faith_id -> row
        self.polity_dynasty = {}  # polity_id -> dynasty_id
        self.polity_faith = {}  # polity_id -> faith_id
        self.polity_monarch = {}  # polity_id -> person_id

    def _add_faith(self, seed_key):
        row = _pick(self.lore.faiths, self.seed, seed_key, 61)
        if row is None:
            row = {"id": "local_0", "name": "社稷", "element_ref": None}
        fid = row["id"]
        if fid not in self.faiths_used:
            self.faiths_used[fid] = {
                "id": fid,
                "name": row["name"],
                "element_ref": row.get("element_ref"),
                "adopted_year": None,
            }
        return fid

    def _add_person(self, *, year, polity_id, dynasty_id, role_key, title=None):
        person_id = len(self.people)
        name = _person_name(self.lore, self.seed, person_id)
        role = _role(self.lore, role_key)
        person = {
            "id": person_id,
            "name": name,
            "role": role,
            "title": title,
            "polity_id": polity_id,
            "dynasty_id": dynasty_id,
            "born": max(0, year - (12 + _mix(self.seed, person_id, 71) % 20)),
            "from_year": year,
            "died": None,
            "until": None,
        }
        self.people.append(person)
        return person_id

    def on_found(self, year, polity_id, emit):
        style = _mix(self.seed, polity_id, year, 7)
        dynasty_id = len(self.dynasties)
        dname = _dynasty_name(self.lore, self.seed, dynasty_id, style)
        title = _title(self.lore, self.seed, dynasty_id)
        monarch_id = self._add_person(
            year=year, polity_id=polity_id, dynasty_id=dynasty_id,
            role_key="monarch", title=title,
        )
        faith_id = self._add_faith(polity_id * 17 + year)
        if self.faiths_used[faith_id]["adopted_year"] is None:
            self.faiths_used[faith_id]["adopted_year"] = year
        self.dynasties.append({
            "id": dynasty_id,
            "name": dname,
            "polity_id": polity_id,
            "founded": year,
            "ended": None,
            "founder_person_id": monarch_id,
            "faith_id": faith_id,
        })
        self.polity_dynasty[polity_id] = dynasty_id
        self.polity_faith[polity_id] = faith_id
        self.polity_monarch[polity_id] = monarch_id
        emit(year, "dynasty", polity_id, None, None,
             "开国王朝「%s」，国教倾向「%s」" % (dname, self.faiths_used[faith_id]["name"]))
        emit(year, "succession", polity_id, None, None,
             "「%s」%s即位" % (title, self.people[monarch_id]["name"]))
        emit(year, "faith_adopt", polity_id, None, None,
             "奉「%s」为国祀" % self.faiths_used[faith_id]["name"])
        # Heir + one courtier
        heir_id = self._add_person(
            year=year, polity_id=polity_id, dynasty_id=dynasty_id, role_key="heir",
        )
        self.people[heir_id]["note"] = "储君"
        minister_key = "general" if style % 3 == 0 else "minister"
        if style % 5 == 0:
            minister_key = "cleric"
        self._add_person(
            year=year, polity_id=polity_id, dynasty_id=dynasty_id, role_key=minister_key,
        )

    def on_fall(self, year, polity_id, emit):
        dynasty_id = self.polity_dynasty.get(polity_id)
        if dynasty_id is not None and self.dynasties[dynasty_id]["ended"] is None:
            self.dynasties[dynasty_id]["ended"] = year
            emit(year, "dynasty", polity_id, None, None,
                 "「%s」随国而终" % self.dynasties[dynasty_id]["name"])
        for person in self.people:
            if person["polity_id"] == polity_id and person["died"] is None:
                person["died"] = year
                person["until"] = year

    def yearly(self, year, living_polity_ids, stream, emit):
        """Succession, appointments, rare faith shifts."""
        reign = max(1, int(getattr(self.config, "reign_years", 18)))
        succ_chance = int(getattr(self.config, "succession_per_mille", 80))
        convert_chance = int(getattr(self.config, "convert_per_mille", 25))
        appoint_chance = int(getattr(self.config, "appoint_per_mille", 40))

        for polity_id in living_polity_ids:
            dynasty_id = self.polity_dynasty.get(polity_id)
            monarch_id = self.polity_monarch.get(polity_id)
            if dynasty_id is None or monarch_id is None:
                continue
            monarch = self.people[monarch_id]
            age_on_throne = year - monarch["from_year"]
            should = age_on_throne >= reign or stream.below(1000) < succ_chance
            if should and age_on_throne >= max(4, reign // 3):
                # End reign
                monarch["died"] = year
                monarch["until"] = year
                # Prefer existing heir
                heir = None
                for person in self.people:
                    if (person["polity_id"] == polity_id and person["died"] is None
                            and person["role"] == _role(self.lore, "heir")):
                        heir = person
                        break
                new_dynasty = stream.below(1000) < int(getattr(self.config, "usurp_per_mille", 120))
                if new_dynasty:
                    self.dynasties[dynasty_id]["ended"] = year
                    emit(year, "dynasty", polity_id, None, None,
                         "「%s」被更替" % self.dynasties[dynasty_id]["name"])
                    style = _mix(self.seed, polity_id, year, 9)
                    new_id = len(self.dynasties)
                    dname = _dynasty_name(self.lore, self.seed, new_id, style)
                    title = _title(self.lore, self.seed, new_id)
                    mid = self._add_person(
                        year=year, polity_id=polity_id, dynasty_id=new_id,
                        role_key="monarch", title=title,
                    )
                    self.dynasties.append({
                        "id": new_id,
                        "name": dname,
                        "polity_id": polity_id,
                        "founded": year,
                        "ended": None,
                        "founder_person_id": mid,
                        "faith_id": self.polity_faith.get(polity_id),
                    })
                    self.polity_dynasty[polity_id] = new_id
                    self.polity_monarch[polity_id] = mid
                    emit(year, "succession", polity_id, None, None,
                         "新朝「%s」：「%s」%s称制" % (dname, title, self.people[mid]["name"]))
                    self._add_person(
                        year=year, polity_id=polity_id, dynasty_id=new_id, role_key="heir",
                    )
                else:
                    title = monarch.get("title") or _title(self.lore, self.seed, year + polity_id)
                    if heir is None:
                        heir_id = self._add_person(
                            year=year, polity_id=polity_id, dynasty_id=dynasty_id,
                            role_key="monarch", title=title,
                        )
                    else:
                        heir_id = heir["id"]
                        heir["role"] = _role(self.lore, "monarch")
                        heir["title"] = title
                        heir["from_year"] = year
                    self.polity_monarch[polity_id] = heir_id
                    emit(year, "succession", polity_id, None, None,
                         "「%s」%s继位" % (title, self.people[heir_id]["name"]))
                    # Refresh heir slot
                    self._add_person(
                        year=year, polity_id=polity_id, dynasty_id=dynasty_id, role_key="heir",
                    )

            if stream.below(1000) < appoint_chance:
                kind = ("general", "minister", "cleric")[
                    _mix(self.seed, year, polity_id, 13) % 3]
                pid = self._add_person(
                    year=year, polity_id=polity_id,
                    dynasty_id=self.polity_dynasty[polity_id],
                    role_key=kind,
                )
                emit(year, "appoint", polity_id, None, None,
                     "任命%s「%s」" % (self.people[pid]["role"], self.people[pid]["name"]))

            if stream.below(1000) < convert_chance and len(self.lore.faiths) > 1:
                old = self.polity_faith.get(polity_id)
                new_faith = self._add_faith(year * 31 + polity_id * 7 + 3)
                if new_faith != old:
                    self.polity_faith[polity_id] = new_faith
                    if self.faiths_used[new_faith]["adopted_year"] is None:
                        self.faiths_used[new_faith]["adopted_year"] = year
                    emit(year, "convert", polity_id, None, None,
                         "国祀改奉「%s」" % self.faiths_used[new_faith]["name"])

    def snapshot_extras(self, living_ids):
        dynasties = []
        for row in self.dynasties:
            if row["polity_id"] in living_ids or row["ended"] is None:
                dynasties.append(dict(row))
        people = []
        for person in self.people:
            if person["polity_id"] in living_ids and person["died"] is None:
                people.append({
                    "id": person["id"],
                    "name": person["name"],
                    "role": person["role"],
                    "title": person.get("title"),
                    "polity_id": person["polity_id"],
                    "dynasty_id": person["dynasty_id"],
                    "born": person["born"],
                    "from_year": person["from_year"],
                })
        faiths = [dict(row) for row in self.faiths_used.values()]
        return {
            "dynasties": dynasties,
            "people": people,
            "faiths": faiths,
            "polity_dynasty": {str(k): v for k, v in self.polity_dynasty.items()},
            "polity_faith": {str(k): v for k, v in self.polity_faith.items()},
            "polity_monarch": {str(k): v for k, v in self.polity_monarch.items()},
        }

    def final_tables(self):
        return {
            "dynasties": [dict(row) for row in self.dynasties],
            "people": [dict(row) for row in self.people],
            "faiths": [dict(row) for row in self.faiths_used.values()],
        }
