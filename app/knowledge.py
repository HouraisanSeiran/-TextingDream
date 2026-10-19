"""File-backed story documents, bounded retrieval and evidence-only dialogue notes."""
import copy
import hashlib
import json
import re
from pathlib import Path
from .prompts import stable_json


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(text, encoding='utf-8')
    temp.replace(path)


def point_document(point):
    meta = {k: v for k, v in point.items() if k != 'content'}
    return '```json\n' + json.dumps(meta, ensure_ascii=False, indent=2) + '\n```\n\n' + point['content'] + '\n'


def read_point(path):
    text = path.read_text(encoding='utf-8-sig')
    match = re.fullmatch(r'```json\s*\n(.*?)\n```\s*\n(.*)', text, re.S)
    if not match:
        raise ValueError(f'知识点文档格式错误：{path.name}')
    p = json.loads(match[1])
    p['content'] = match[2].strip()
    return p


def validate_points(points):
    ids = set()
    for p in points:
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', p.get('id', '')) or p['id'] in ids:
            raise ValueError('知识点 ID 无效或重复')
        ids.add(p['id'])
        if p.get('visibility') not in ('public', 'author'):
            raise ValueError('知识点需明确 public 或 author 可见性')
        if not isinstance(p.get('keywords'), list) or not all(isinstance(k, str) and k for k in p['keywords']):
            raise ValueError('知识点关键词必须是非空字符串列表')
        if not isinstance(p.get('content'), str) or not p['content'].strip() or len(p['content']) > 6000:
            raise ValueError('知识点正文不能为空或超过 6000 字符，请拆分')
    for p in points:
        if set(p.get('requires', [])) - ids:
            raise ValueError('知识点依赖不存在')


class PackageFiles:
    def __init__(self, directory):
        self.directory = Path(directory)

    def read(self):
        # Only this selected package is read. Generated journey notes are never world canon.
        story = json.loads((self.directory / 'story.json').read_text(encoding='utf-8-sig'))
        overview = (self.directory / '总概.md').read_text(encoding='utf-8-sig').strip()
        points = []
        for file in sorted((self.directory / '知识点').rglob('*.md')):
            if file.is_symlink():
                raise ValueError('知识点不支持符号链接')
            points.append(read_point(file))
        validate_points(points)
        story['worldview'] = {'premise': overview}
        story['knowledge'] = points
        atlas_file = self.directory / 'atlas.json'
        if atlas_file.exists():
            if atlas_file.is_symlink():
                raise ValueError('地图文档不支持符号链接')
            story['atlas'] = json.loads(atlas_file.read_text(encoding='utf-8-sig'))
        story['public_lore'] = {'premise': overview}
        return story

    def write(self, story):
        validate_points(story.get('knowledge', []))
        base = copy.deepcopy(story)
        atlas = base.pop('atlas', None)
        # An explicit empty atlas clears a previously saved map as well.
        if atlas is not None or (self.directory / 'atlas.json').exists():
            atomic_text(self.directory / 'atlas.json', json.dumps(atlas or {'version':1,'features':[]}, ensure_ascii=False, indent=2))
        points = base.pop('knowledge', [])
        worldview = base.pop('worldview', {})
        overview = worldview.get('premise', base['premise'])
        base.pop('public_lore', None)
        # Non-overview author edits are retained as individual author knowledge points.
        for key, value in worldview.items():
            if key == 'premise':
                continue
            pid = 'worldview_' + hashlib.sha256(key.encode()).hexdigest()[:12]
            points = [p for p in points if p['id'] != pid]
            points.append({'id': pid, 'title': key, 'category': '作者补充', 'keywords': [key],
                           'visibility': 'author', 'status': 'author_setting',
                           'content': json.dumps(value, ensure_ascii=False, indent=2)})
        validate_points(points)
        existing = {}
        for file in sorted((self.directory / '知识点').rglob('*.md')):
            existing[read_point(file)['id']] = file
        for point in points:
            category = re.sub(r'[^\w\u4e00-\u9fff-]', '_', point.get('category', '未分类'))
            path = existing.get(point['id'], self.directory / '知识点' / category / (point['id'] + '.md'))
            text = point_document(point)
            if not path.exists() or path.read_text(encoding='utf-8') != text:
                atomic_text(path, text)
        # Retired documents are retained outside the active retrieval directory.
        for pid in existing.keys() - {p['id'] for p in points}:
            target = self.directory / '历史文档' / (pid + '.md')
            target.parent.mkdir(parents=True, exist_ok=True)
            existing[pid].replace(target)
        atomic_text(self.directory / '总概.md', overview + '\n')
        atomic_text(self.directory / 'story.json', json.dumps(base, ensure_ascii=False, indent=2) + '\n')

    def save_notes(self, scope, identifier, notes):
        if scope not in ('旅程', '里层草稿') or not re.fullmatch(r'[a-zA-Z0-9_-]+', identifier):
            raise ValueError('记录路径无效')
        text = '# ' + scope + '知识点 · ' + identifier + '\n\n此处是生成记录，不自动成为世界真相；不跨旅程检索。\n\n'
        for n in notes:
            text += '## ' + n['title'] + '\n\n' + point_document(n) + '\n'
        atomic_text(self.directory / '生成记录' / scope / (identifier + '.md'), text)


def retrieve(story, query, audience='player', location=None, flags=None, limit=6, budget=3600):
    flags = flags or {}
    allowed = []
    for p in story.get('knowledge', []):
        if audience != 'author':
            if p.get('visibility') != 'public':
                continue
            if p.get('known_by') and audience not in p['known_by']:
                continue
            if p.get('reveal_flag') and not flags.get(p['reveal_flag']):
                continue
            if p.get('locations') and location not in p['locations']:
                continue
        allowed.append(p)
    query = query.casefold()
    def score(p):
        explicit = sum(min(len(k), 8) for k in p['keywords'] if k.casefold() in query)
        return explicit * 10 + (2 if location and location in p.get('locations', []) else 0)
    ranked = sorted(allowed, key=lambda p: (-score(p), p['id']))
    by_id = {p['id']: p for p in allowed}
    selected, visited = [], set()
    def collect(p, chain):
        if p['id'] in chain or p['id'] in visited:
            return []
        chain = chain | {p['id']}
        group = []
        for dependency in p.get('requires', []):
            if dependency not in by_id:
                return None
            children = collect(by_id[dependency], chain)
            if children is None:
                return None
            group.extend(children)
        group.append(p)
        return group
    for p in ranked:
        if score(p) <= 0 or p['id'] in visited:
            continue
        group = collect(p, set())
        if group is None:
            continue
        unique = {x['id']: x for x in group if x['id'] not in visited}
        projected = [{'id': x['id'], 'title': x['title'], 'status': x.get('status', 'setting'), 'content': x['content']} for x in unique.values()]
        if len(selected) + len(projected) > limit or len(stable_json(selected + projected)) > budget:
            continue
        selected.extend(projected)
        visited.update(unique)
    return selected


def extract_notes(text, source, vocabulary=()):
    """Extract complete paragraphs, never complete a name using unseen world knowledge."""
    notes = []
    for paragraph in re.split(r'\n\s*\n|\n', text):
        paragraph = paragraph.strip()
        if len(paragraph) < 10:
            continue
        vocabulary = vocabulary or ('万言机', '翻译', '关城', '文书', '守卫', '商人', '道路', '封闭', '传闻', '书信',
                                    '季风', '船队', '港口', '契约', '见证人', '失约', '粮食', '水源', '灵气', '修炼',
                                    '天朝', '新月', '圣教', '寺院', '继位', '金币', '银币', '铜匣', '纸条', '秘密')
        keys = sorted({k for k in vocabulary if k in paragraph}, key=lambda k: (-len(k), k))[:8]
        if not keys:
            # Local keywords are a search aid, not a second AI assertion.
            keys = list(dict.fromkeys(re.findall(r'[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}', paragraph)))[:6]
        sentences = re.findall(r'.+?(?:[。！？](?:[”’」』])?|$)', paragraph)
        summary = ''.join(sentences[:2]) or paragraph
        # A qualification can occur at the end; do not crop it out of the preview.
        if any(word in paragraph for word in ('不', '未', '没有', '传闻', '据说', '听说', '声称', '谎', '否认', '但是', '然而')):
            summary = paragraph
        identity = hashlib.sha256((source['id'] + paragraph).encode()).hexdigest()[:20]
        notes.append({'id': 'note_' + identity, 'title': ' / '.join(keys[:3]) or '对话见闻',
                      'keywords': keys, 'summary': summary, 'content': paragraph,
                      'status': '对话所闻，未独立核实', 'source': source,
                      'origin': 'prose',
                      'visibility': 'player' if source['scope'] == 'surface' else 'author'})
    return notes


def confirmed_notes(session):
    """Records the rules engine itself wrote and marked as confirmed.

    Only `distortion == 0` with an explicit `source` qualifies; speech, rumors and
    notices carry their distortion and stay unverified narrative. These come back
    before prose-derived notes because they have the same authority as the state
    they came from, while a reply is only evidence of what was said.
    """
    result, seen = [], set()
    for record in session.get('heard', []):
        text = record.get('text')
        if record.get('distortion') != 0 or not record.get('source') or not isinstance(text, str):
            continue
        if text in seen:
            continue
        seen.add(text)
        keys = list(dict.fromkeys(re.findall(r'[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}', text)))[:6]
        result.append({'id': 'confirmed_' + str(record.get('id') or hashlib.sha256(text.encode()).hexdigest()[:20]),
                       'title': ' / '.join(keys[:3]) or '已确认记录',
                       'keywords': keys, 'summary': text, 'content': text,
                       'status': '状态层已确认', 'origin': 'confirmed',
                       'source': {'id': record['source'], 'scope': 'state', 'event': '状态层记录'},
                       'visibility': 'player'})
    return result


def notebook(session):
    result = confirmed_notes(session)
    for event in session['archives'] + ([session['active']] if session['active'] else []):
        for index, turn in enumerate(event['turns']):
            source = {'id': event['id'] + ':' + str(index), 'scope': 'surface',
                      'event': event['title'], 'conversation': event.get('conversation', {}).get('id')}
            # Stored notes are not trusted; derive again from the displayed reply only.
            result.extend(extract_notes(turn['reply'], source))
    return result
