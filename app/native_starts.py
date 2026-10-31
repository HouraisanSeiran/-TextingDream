# -*- coding: utf-8 -*-
"""从 civ 地图 + 选定历史创建**首个故事**（空态 → 可 new_session）。

三段式，每段都有自己的边界：

1. :func:`preview` —— 纯读。用真实 civ 在该年份的实体列出可选城市与玩家起点，
   不写任何东西（不建 package / pointer / session）。
2. :func:`save` —— 存一份**开局候选**（``ns_``）：来源三键与登记记录自洽、城市在该年
   存续、起点 cell 必须就是该城 cell。仍然不建包。
3. :func:`confirm` —— 作者显式确认后，才用既有 ``Runtime.commit_package`` 事务建首包。

三条不做：

* 不造坐标：``locations`` 不写作者没提供的 ``coordinates``（没有就留空，由既有
  ``play_map`` 按 ``null`` 处理）。
* 普通开局保留原有空路线；显式 exploration 开局通过 civ_exploration
  编译该年份的原件道路与生成街区，不修改已有旅程。
* 不新造历史库：快照来自既有 ``world_history_store``（已 review + commit 的那份）。
"""
from __future__ import annotations

import json
import re
import uuid

from . import civ_atlas_history, civ_atlas_snapshot, native_worlds, world_history_store, civ_exploration

KIND = 'native_start'
ID_PREFIX = 'ns_'
_ID_RE = re.compile(r'^ns_[0-9a-f]{16}$')
MAX_TITLE = 80
MAX_PREMISE = 2000
MAX_TEXT = 400

#: 本阶段明确的边界：没有合法路资料，首包不造任何城市间旅行路。
TRAVEL_UNAVAILABLE = 'unavailable_no_road_data'


def _text(value, label, limit, required=True):
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise ValueError('%s 必须是文本' % label)
    text = value.strip()
    if required and not text:
        raise ValueError('%s 不能为空' % label)
    if len(text) > limit:
        raise ValueError('%s 不能超过 %d 字' % (label, limit))
    return text


def _year(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('基年必须是数字')
    if not 0 <= value <= 100000:
        raise ValueError('基年超出可接受范围')
    return float(value)


def _hex64(value, label):
    text = str(value or '').lower()
    if not re.fullmatch(r'[0-9a-f]{64}', text):
        raise ValueError('%s 必须是 64 位十六进制' % label)
    return text


def _record(store, import_id):
    """取一条原生快照记录（复用原生桥：格式不对/不存在都抬可读错误）。"""
    return native_worlds._record(store, import_id)


def _civ(store, record):
    """读原件里的 civ（字节校验走已验的原生桥，不自己拼路径/算哈希）。"""
    from pathlib import Path
    data, _checked = native_worlds.snapshot_bytes(
        store, Path(store.path).resolve().parent, record['id'])
    return civ_atlas_history.load_civ(data)[0]


SNAPSHOT_KIND = world_history_store.SNAPSHOT_KIND


def _snapshot(store, snapshot_id):
    """读一份已固定的历史快照（直读 store；不依赖 Service 实例方法）。"""
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith('hs_'):
        raise ValueError('历史快照编号格式不对')
    row = store.get(SNAPSHOT_KIND, snapshot_id)
    if not row:
        raise ValueError('找不到这份历史快照')
    return row


def _world_and_civ(store, record):
    """一次读原件，拿 (civ, World)。两样都来自同一份已校验字节。"""
    from pathlib import Path
    data, _checked = native_worlds.snapshot_bytes(
        store, Path(store.path).resolve().parent, record['id'])
    manifest, parts = civ_atlas_snapshot.parse_container(data)
    return (civ_atlas_history.decode_civ_part(manifest, parts),
            civ_atlas_snapshot.read_world(manifest, parts))


def cell_position(world, cell):
    """把 civ 的 cell 编号换成真实 ``[lon, lat]``，不做任何示意或捏造。

    坐标来自原件自己的 ``World.mesh.x/y``（``read_world`` 已经把每格的经纬算好），
    与 ``civ_atlas_snapshot.sample_region`` 用的是同一套值；cell 越界就是越界，
    不返回近似点。
    """
    if isinstance(cell, bool) or not isinstance(cell, int):
        raise ValueError('cell 必须是整数')
    if not 0 <= cell < world.cells:
        raise ValueError('cell 超出原件网格范围（0…%d）' % (world.cells - 1))
    lon = world.lon[cell]
    lat = world.lat[cell]
    if lon is None or lat is None:
        raise ValueError('原件没有给出该 cell 的经纬投影')
    return [round(float(lon), 6), round(float(lat), 6)]


def settlements_at(civ, year):
    """该年份**存续**的城：建城年 ≤ year 且（没有结束年或 year < 结束年）。

    与 ``civ_atlas_history`` 回放用的同一判据，不另立一套口径；未来城市不会出现。
    """
    rows = []
    for row in civ.get('settlements') or ():
        if not isinstance(row, dict):
            continue
        entity = row.get('id')
        founded = row.get('founded')
        ended = row.get('ended')
        if isinstance(entity, bool) or not isinstance(entity, int) or entity < 0:
            continue
        if isinstance(founded, bool) or not isinstance(founded, (int, float)):
            continue
        if not founded <= year:
            continue
        if isinstance(ended, (int, float)) and not isinstance(ended, bool) and not year < ended:
            continue
        rows.append({'city_id': 'settlement:%d' % entity, 'name': row.get('name') or '',
                     'cell': row.get('cell'), 'region': row.get('region'),
                     'founded': founded})
    rows.sort(key=lambda row: row['city_id'])
    return rows


def preview(store, import_id, *, base_year, branch='main'):
    """可选城市与开局参考（纯读；空态也能调）。"""
    record = _record(store, import_id)
    year = _year(base_year)
    name = _text(branch, '分支', 120, required=False) or 'main'
    civ, world = _world_and_civ(store, record)
    rows = settlements_at(civ, year)
    # 每个城附上它自己 cell 的真实经纬（来自原件网格），不给示意坐标。
    for row in rows:
        try:
            row['position'] = cell_position(world, row.get('cell'))
        except ValueError:
            row['position'] = None
    source = record.get('source') or {}
    return {
        'import_id': record['id'],
        'source_sha256': record.get('sha256'),
        'world_id': source.get('world_id'),
        'branch': name,
        'base_year': year,
        'settlements': rows[:400],
        'counts': {'returned': min(len(rows), 400), 'truncated': len(rows) > 400},
        # 历史适配校验沿用既有 world_history_store 的口径（同一年份同一份原件）。
        'terrain': {'status': 'from_snapshot',
                    'note': '地形/历史同源；是否匹配由回放时的 terrain 校验给出'},
        'travel': TRAVEL_UNAVAILABLE,
        'exploration': {'available': bool(rows), 'live_routes': len(civ_exploration.live_routes(civ, year)),
                        'town_limit': civ_exploration.TOWN_LIMIT},
        'warnings': ['普通开局不启用旅行；选择城镇探索可生成道路与街区'],
    }


def _check_city(civ, city_id, year):
    """城市必须在该年存续；否则告诉作者具体原因（不按同名造城）。"""
    match = re.fullmatch(r'settlement:([0-9]{1,12})', str(city_id or ''))
    if not match:
        raise ValueError('city_id 必须是 settlement:<数字>')
    wanted = int(match.group(1))
    rows = {row['city_id']: row for row in settlements_at(civ, year)}
    row = rows.get('settlement:%d' % wanted)
    if row is None:
        raise ValueError('这个城市在基年 %g 不存在（未建城或已结束），'
                         '不能拿未来城市或同名新城开局' % year)
    return row


def build_body(store, request):
    """校验并组装一份候选（不写库）。返回 ``(doc, record)``。"""
    if not isinstance(request, dict):
        raise ValueError('开局请求必须是对象')
    extra = set(request) - {'import_id', 'source_sha256', 'world_id', 'branch', 'base_year',
                            'city_id', 'title', 'premise', 'motive', 'local_problem',
                            'start_cell', 'history_snapshot_id', 'exploration'}
    if extra:
        raise ValueError('开局请求有未知字段：%s' % '、'.join(sorted(extra)))
    if type(request.get('exploration', False)) is not bool:
        raise ValueError('exploration 必须是布尔值')
    record = _record(store, request.get('import_id'))
    digest = _hex64(request.get('source_sha256'), '来源哈希')
    if digest != record.get('sha256'):
        raise ValueError('来源哈希与登记的原件不符，拒绝开局')
    world_id = (record.get('source') or {}).get('world_id')
    if request.get('world_id') != world_id:
        raise ValueError('world_id 与登记的原件不一致')
    year = _year(request.get('base_year'))
    branch = _text(request.get('branch'), '分支', 120, required=False) or 'main'
    civ = _civ(store, record)
    city = _check_city(civ, request.get('city_id'), year)
    start_cell = request.get('start_cell')
    if start_cell is not None:
        if isinstance(start_cell, bool) or not isinstance(start_cell, int):
            raise ValueError('起点 cell 必须是整数')
        if city.get('cell') is not None and start_cell != city['cell']:
            raise ValueError('玩家起点必须在该城市的 cell 上（%s）' % city['cell'])
    snapshot_id = request.get('history_snapshot_id')
    snapshot = None
    if snapshot_id is not None:
        snapshot = _snapshot(store, snapshot_id)
        # 同一份原件、**同一个年份与分支**才能采纳：不同年份/分支不是同一段历史。
        if snapshot.get('import_id') != record['id']:
            raise ValueError('历史快照与本开局不是同一份原件')
        if (snapshot.get('source') or {}).get('content_sha256') != digest:
            raise ValueError('历史快照的内容哈希与本开局不一致')
        if float(snapshot.get('base_year')) != year:
            raise ValueError('历史快照的基年（%s）与本开局（%g）不一致，不能同权采纳'
                             % (snapshot.get('base_year'), year))
        if (snapshot.get('branch') or 'main') != branch:
            raise ValueError('历史快照的分支（%s）与本开局（%s）不一致，不能同权采纳'
                             % (snapshot.get('branch'), branch))
        if not (snapshot.get('for_author_review') and not snapshot.get('auto_canonical')):
            raise ValueError('历史快照必须已经过作者审阅与固定')
    doc = {
        'id': ID_PREFIX + uuid.uuid4().hex[:16],
        'kind': KIND,
        'schema': 1,
        'revision': 0,
        'status': 'candidate',
        'import_id': record['id'],
        'source_sha256': digest,
        'world_id': world_id,
        'branch': branch,
        'base_year': year,
        'city_id': city['city_id'],
        'city_name': city.get('name'),
        'start_cell': start_cell if start_cell is not None else city.get('cell'),
        'title': _text(request.get('title'), '标题', MAX_TITLE),
        'premise': _text(request.get('premise'), '前提', MAX_PREMISE),
        'motive': _text(request.get('motive'), '动机', MAX_TEXT, required=False),
        'local_problem': _text(request.get('local_problem'), '地方问题', MAX_TEXT,
                               required=False),
        'history_snapshot_id': snapshot_id,
        # 开局身份：空态回放只能钉在这上面（见 world_history_store._story_pin）。
        'identity_locked': True,
        'travel': 'civ_routes_and_town_streets' if request.get('exploration') else TRAVEL_UNAVAILABLE,
        'exploration': request.get('exploration', False),
    }
    return doc, record


def save(store, request):
    """存一份候选。**不建 package / pointer / session**。"""
    doc, _record_row = build_body(store, request)
    with store.transact() as db:
        db.execute('INSERT INTO documents(kind,id,body) VALUES(?,?,?)',
                   (KIND, doc['id'], __import__('json').dumps(doc, ensure_ascii=False,
                                                              separators=(',', ':'))))
    return {'draft': doc, 'created': True}


def get(store, draft_id):
    if not isinstance(draft_id, str) or not _ID_RE.fullmatch(draft_id):
        raise ValueError('开局草稿编号格式不对')
    row = store.get(KIND, draft_id)
    if not row:
        raise ValueError('找不到这个开局草稿')
    return row


def list_all(store):
    return sorted(store.all(KIND), key=lambda row: (row.get('id') or ''))


def start_key(doc):
    """开局草稿的稳定身份，供历史回放草稿钉住（``start:<key>``）。"""
    return doc['id']


def _story_and_characters(store, doc, *, service=None):
    """首包：地点只来自真实 civ 城；坐标由真实 cell 投影得来；不造旅行路。"""
    record = _record(store, doc['import_id'])
    civ, world = _world_and_civ(store, record)
    rows = settlements_at(civ, doc['base_year'])
    if not rows:
        raise ValueError('基年 %g 没有任何存续城市，无法建首包' % doc['base_year'])
    locations = []
    for row in rows:
        # 坐标来自原件网格（``World.mesh.x/y``）；推不出就留空，而不是写一个示意点。
        try:
            position = cell_position(world, row.get('cell'))
            position_source = 'snapshot_mesh_cell'
        except ValueError:
            position = None
            position_source = 'unrecorded'
        entry = {
            'id': 'city_%d' % int(row['city_id'].split(':')[1]),
            'name': row.get('name') or row['city_id'],
            'description': '',
            # 故意为空：本阶段没有任何合法路资料。
            'neighbors': [],
            'scenes': [],
            'civ_ref': {'import_id': doc['import_id'],
                        'source_sha256': doc['source_sha256'],
                        'city_id': row['city_id'],
                        'cell': row.get('cell'),
                        'position_source': position_source},
        }
        if position is not None:
            entry['coordinates'] = position
        locations.append(entry)
    start_id = 'city_%d' % int(doc['city_id'].split(':')[1])
    story = {
        'id': 'native_' + doc['id'],
        'title': doc['title'],
        'premise': doc['premise'],
        'character_package_id': 'native_' + doc['id'] + '_characters',
        'locations': locations,
        # 只造一个起点事件：人物任务/战斗是后续阶段。
        'events': [{
            'id': 'opening', 'title': doc['title'], 'location_id': start_id,
            'participants': ['player'], 'player_goal': doc.get('motive') or '看看这里',
            'player_enters': True, 'next_events': [], 'entry_flags': {},
            'exit_flag': 'opening_done', 'max_turns': 12,
            'actions': [{'id': 'look_around', 'label': '看看四周', 'ends_event': True,
                         'success_text': doc.get('local_problem') or '我看了看四周。'}],
        }],
        'items': [],
        'mechanics': {
            'local': {'turn_hours': 1, 'travel_hours': 2},
            'map': {'kind': 'civ_atlas', 'import_id': doc['import_id']},
        },
    }
    axes = {'talent': 50, 'strength': 50, 'agility': 50, 'wisdom': 50,
            'social': 50, 'resilience': 50}
    characters = {'id': story['character_package_id'], 'title': doc['title'],
                  'characters': [{'id': 'player', 'name': '我', 'role': '主角',
                                  'location_id': start_id, 'personality': {},
                                  'state': {}, 'attributes': dict(axes)}]}
    if doc.get('history_snapshot_id'):
        snapshot = _snapshot(store, doc['history_snapshot_id'])
        # 采纳历史仍走既有 adopt 语义：快照写进新 revision 的 mechanics.history。
        story['mechanics']['history'] = {
            'schema': world_history_store.MECHANICS_SCHEMA,
            'entries': [_adopted_entry(snapshot)],
        }
    if doc.get('exploration'):
        return civ_exploration.compile_region(story, characters, civ, world, doc, rows)
    return story, characters


def _adopted_entry(snapshot):
    return {'snapshot_id': snapshot['id'], 'import_id': snapshot['import_id'],
            'base_year': snapshot['base_year'], 'branch': snapshot['branch'],
            'digest': snapshot['digest'],
            'content_sha256': (snapshot.get('source') or {}).get('content_sha256'),
            'story_id': (snapshot.get('story') or {}).get('story_id'),
            'note': '由开局草稿采纳',
            'snapshot': {key: value for key, value in snapshot.items()
                         if key not in ('id', 'digest', 'created')}}


def confirm(runtime, store, draft_id, *, expected_revision):
    """作者显式确认 → 用既有事务建首包。

    双并发与重试都必须只产生**一个**包，所以顺序是：

    1. **先在同一事务里原子占位**（条件更新：revision 仍是 expected_revision 且还没
       占位才成功）。两个并发请求只能一个拿到占位，另一个被拒；不会两个都去建包。
    2. 占位后才调既有 ``commit_package``（它自己就是包事务）。
    3. 写回 revision：若 commit 成功但写回失败，重试（仍带原 expected_revision）
       会看到已占位，于是用占位里记录的 ``start_key`` 找回**同一个**包，
       返回``created: False``，不建第二个。

    幂等锚是包内稳定的 ``native_start_key``：即使索引行丢了，也能从包里认回来。
    """
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
        raise ValueError('乐观版本号必须是整数')
    doc = get(store, draft_id)
    # 已确认过（或上次 commit 成功但写回失败）：直接找回同一个包。
    recovered = _existing_package(runtime, store, doc)
    if recovered is not None:
        revision, package = recovered
        _mark_confirmed(store, doc, revision, force=True)
        return {'revision': revision, 'created': False,
                'world': _world_view(runtime, package, store)}
    # 原子占位：同一瞬间只能一个请求过。
    claimed = _claim(store, doc, expected_revision)
    if not claimed:
        doc = get(store, draft_id)
        recovered = _existing_package(runtime, store, doc)
        if recovered is not None:
            revision, package = recovered
            return {'revision': revision, 'created': False,
                    'world': _world_view(runtime, package, store)}
        raise ValueError('开局草稿已被其他操作更新（当前版本 %s，提交版本 %s），请刷新后重试'
                         % (doc.get('revision'), expected_revision))
    story, characters = _story_and_characters(store, doc)
    # 包内稳定锚：重试时靠它认回同一个包，不依赖索引行是否已写。
    story['native_start_key'] = doc['id']
    revision = runtime.commit_package(story, characters, '从 civ 开局：' + doc['title'])
    _mark_confirmed(store, doc, revision, force=True)
    package = store.get('package', revision)
    return {'revision': revision, 'created': True,
            'world': _world_view(runtime, package, store)}


def _existing_package(runtime, store, doc):
    """用稳定锚找回这个开局已经建过的包（不扫描非本开局的包）。"""
    if doc.get('confirmed_revision'):
        package = store.get('package', doc['confirmed_revision'])
        if package:
            return doc['confirmed_revision'], package
    for package in store.all('package'):
        if (package.get('story') or {}).get('native_start_key') == doc['id']:
            return package['id'], package
    return None


def _claim(store, doc, expected_revision):
    """在同一写事务里条件占位：版本对且未占位才成功。"""
    with store.transact() as db:
        row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                         (KIND, doc['id'])).fetchone()
        if row is None:
            raise ValueError('找不到这个开局草稿')
        latest = json.loads(row[0])
        if int(latest.get('revision') or 0) != expected_revision:
            return False
        if latest.get('confirmed_revision'):
            return False
        latest['claim'] = True
        db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                   (KIND, doc['id'], json.dumps(latest, ensure_ascii=False,
                                                separators=(',', ':'))))
        return True


def _mark_confirmed(store, doc, revision, *, force=False):
    with store.transact() as db:
        row = db.execute('SELECT body FROM documents WHERE kind=? AND id=?',
                         (KIND, doc['id'])).fetchone()
        latest = json.loads(row[0]) if row else dict(doc)
        latest.pop('claim', None)
        latest['status'] = 'confirmed'
        latest['confirmed_revision'] = revision
        latest['revision'] = int(latest.get('revision') or 0) + 1
        db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',
                   (KIND, doc['id'], json.dumps(latest, ensure_ascii=False,
                                                separators=(',', ':'))))


def _world_view(runtime, package, store):
    if not package:
        return None
    story = package['story']
    return {'revision': package['id'], 'title': story.get('title'),
            'story_id': story.get('id'),
            'places': len(story.get('locations') or [])}
