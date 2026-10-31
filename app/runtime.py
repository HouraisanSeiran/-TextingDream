"""UI-independent director, package revisions, projections and event snapshots."""
import copy
import hashlib
import json
import re
import uuid
import shutil
from datetime import datetime, timezone
from .contracts import Element
from .models import StoryAssembly
from .knowledge import PackageFiles, retrieve, notebook, validate_points, atomic_text, fsync_directory
from . import package_transaction
from .recall import Recall, dialogue_records, vector
from .context_stage import stage_history
from .summary import event_summary, has_excerpt, strip_excerpt, with_stage
from .drama import resolve_check, outcome_cues, validate_cues, public_voice, cast_projection
from . import local_rules
from . import rewards as rewards_rules
from . import pressure as pressure_rules
from . import traits as traits_rules
from . import start_profiles as start_rules
from . import endings as endings_rules
from . import free_actions
from . import scene_judgment
from . import npc_cards
from . import civ_exploration
from . import adventure_actions
from .state_anchor import state_anchor
from .atlas import validate_atlas, project_atlas
from . import attributes
from . import element_assembly
from . import towns_store
from . import play_map
from . import world_history_store
from .geography import Environment, Calendar, local_environment, is_daylight


def uid():
    return uuid.uuid4().hex[:16]


def now():
    return datetime.now(timezone.utc).isoformat()


def chars(value):
    return len(json.dumps(value, ensure_ascii=False))


def revision_folder_slug(story_id):
    """把一个故事 id 变成合法的包目录名（首次创建世界时用）。

    只用 ASCII 字母数字与下划线：旧预制目录名（如「玄陆」）不再被当成默认值，
    也不会因为 id 里带中文或符号而写到非法路径。冲突时后缀由调用方自行处理。
    """
    text = re.sub(r'[^A-Za-z0-9_]+', '_', str(story_id or '')).strip('_')
    return (text or 'untitled')[:40]


def _reject_reserved_action_ids(story):
    """``adventure:`` 前缀保留给运行时算出来的方案。

    只在包声明了 ``mechanics.adventure`` 时生效：老包里作者可能真有一个叫
    ``adventure:xx`` 的静态动作，那时一个字节也不改。新机制包里如果还用这个前缀，
    同一个 id 会同时指静态动作与动态方案，界面与确认凭据都会歧义，所以在打包时拒绝。
    """
    if adventure_actions.config(story) is None:
        return
    for event in story.get('events') or []:
        for action in event.get('actions') or []:
            if str(action.get('id', '')).startswith(adventure_actions.ID_PREFIX):
                raise ValueError('事件 %s 的动作 %r 占用了保留前缀 %r（运行时方案专用）'
                                 % (event.get('id'), action.get('id'),
                                    adventure_actions.ID_PREFIX))


#: 世界历史进入 prompt/surface 的上限：条目数与字符数都有界，空结果不加 key。
WORLD_HISTORY_MAX_ITEMS = 8
WORLD_HISTORY_MAX_CHARS = 1200
#: 只透传这些字段（与 ``world_history_store.PUBLIC_ENTRY_FIELDS`` 的白名单同源）。
WORLD_HISTORY_FIELDS = ('category', 'ref', 'year', 'kind', 'region', 'settlement_ref',
                        'display_name', 'founded', 'role', 'location_id', 'summary')

# Drop model-derived material first, engine-sourced material last: the model's own
# prose is re-derivable from the replies still kept in `history`, whereas the world
# canon in `knowledge` and the settlement in `last_summary` have no other copy in
# the prompt. Whole entries only; a cut line would be a malformed claim.
TRIM_ORDER = ('dialogue_knowledge', 'recalled_dialogue', 'history', 'memories',
              'current_world_history',
              'current_pressure', 'current_traits', 'npc_cards', 'current_elements', 'elements',
              'knowledge')
# ``current_world_history`` 是 dict 型块（``{'items': [...]}``），与 ``history``
# （对话轮次列表）**不是一个东西**；它排在 memories 之后先被裁，因为世界设定比当下对话
# 更好重取，且裁剪是整条丢弃、绝不切半句。
# 基线里就以「列表」存在的键：清空后仍以 [] 保留（下游按「键在、可为空」写）。
TRIM_LIST_KEYS = ('dialogue_knowledge', 'recalled_dialogue', 'history', 'memories',
                  'elements', 'knowledge')


def budget_for(preferences):
    """The one character budget shared by every dynamic block.

    Elements, traits and known warnings are NOT given extra room on top of this: the
    caller hands each of them the remaining space and `trim_context` can drop them
    again, so declaring a new block can never make a prompt larger than the budget.
    """
    return preferences['context_chars'] - 3000


def trim_context(result, budget):
    """Drop whole entries until the prompt fits; never slice a sentence.

    三条契约：

    1. 列表型内容块（`TRIM_LIST_KEYS`）**总是以容器存在**（启动时补齐为 `[]`，清空后仍保留 `[]`）——
       下游有按「键在、可为空」读的地方（例如事件摘要回归读 `trimmed['dialogue_knowledge']`）。
    2. 没声明新机制的旧包，`current_pressure` / `current_traits` / `current_elements`
       **不会被凭空插入**：缺键就保持缺键，旧包的 prompt 一个字也不多。
    3. 按 `TRIM_ORDER` 的优先级**级联**裁剪：先清完前一个块，再动下一个；
       dict 型块（压力/特质/元素清单）只在它**本来就在**、且 `items` 被清空时才整个移除。
    """
    for key in TRIM_LIST_KEYS:
        result.setdefault(key, [])
    while chars(result) > budget:
        for key in TRIM_ORDER:
            item = result.get(key)
            if isinstance(item, dict):
                entries = item.get('items')
                if entries:
                    entries.pop()
                    if not entries:
                        result.pop(key, None)
                    break
                # 已经是空壳的 dict 块：直接移除，不留在 prompt 里。
                result.pop(key, None)
                break
            elif item:
                item.pop(0 if key in ('history', 'dialogue_knowledge') else -1)
                break
        else:
            break
    if chars(result) > budget and has_excerpt(result.get('last_summary')):
        result['last_summary'] = strip_excerpt(result['last_summary'])
    if chars(result) > budget:
        # The archive keeps every turn; the prompt copy is only a convenience.
        result['last_summary'] = ''
    return result


class Runtime:
    def __init__(self, store, root):
        self.store, self.root = store, root
        self.recall = Recall(store)
        self.attribute_vectors = attributes.KeywordVectors(store)
        # 不再自动导入任何预制世界：
        # 旧实现会在生产根里硬找 ``StoryPackage/玄陆``、``world_packages/玄陆_世界包.json``
        # 与 ``character_packages/xuanlu_初始角色包.json`` 并直接在启动时提交成包 —— 用户
        # 删掉旧故事后那里再也不会有人希望它回来。现在启动只做准备，有没有世界由数据说话。
        production = store.path.resolve() == (root / 'data/textiledream.sqlite3').resolve()
        self.library = root / 'StoryPackage' if production else store.path.parent / 'StoryPackage'
        self.character_directory = root / 'character_packages' if production else store.path.parent / 'character_packages'
        self.library.mkdir(parents=True, exist_ok=True)
        self.character_directory.mkdir(parents=True, exist_ok=True)
        self._recover_package_transaction()
        pointer = store.get('pointer', 'package')
        self.files = None
        if pointer:
            folder = pointer.get('folder')
            if not folder:
                raise ValueError('已启用故事包记录缺少目录名，请检查存档')
            directory = self.package_directory(folder)
            if not directory.exists():
                raise ValueError('已启用故事包目录不存在：' + folder)
            self.files = PackageFiles(directory)
            if (directory / 'story.json').exists():
                self.reload_documents()
            else:
                raise ValueError('已启用故事包缺少 story.json：' + folder)
        else:
            # 没有 pointer 就是**没有世界**：不构造隐藏默认故事，也不提交空包。
            # 已经躺在库里但没被 pointer 指向的旧包不是当前世界，也不去猜。
            self.files = None
        old_default = '用第一人称写简短小说段落。只描述可见信息，不替玩家决定意图。失败也要带来后续线索。不得将传闻写成已证实事实。'
        corpus = store.get('corpus', 'general')
        if not corpus:
            store.put('corpus', 'general', {'text': ''})
        elif corpus.get('text') == old_default:
            store.put('corpus', 'default_before_compaction', corpus)
            store.put('corpus', 'general', {'text': ''})
        # Backfill old dialogue and repair derived note documents from committed saves.
        # 没有世界时一个旅程也不该存在；旧旅程指向的包已不在就跳过它，不做删除。
        for session in store.all('session'):
            if not store.get('package', session.get('revision')):
                continue
            self.session_files(session).save_notes('旅程', session['id'], notebook(session))

    def package_directory(self, folder):
        if not folder or folder.startswith('.') or '/' in folder or '\\' in folder or ':' in folder:
            raise ValueError('故事包目录名无效')
        path = self.library / folder
        if path.resolve().parent != self.library.resolve():
            raise ValueError('故事包目录必须位于 StoryPackage 内')
        return path

    def _recover_package_transaction(self):
        """Finish or undo an interrupted commit. Repeatable: re-running is a no-op.

        The outcome comes from the committed pointer plus the disk layout, never from a
        single flag, so an interruption during an earlier recovery still converges. A
        journal that fails validation keeps every file untouched and raises: the author
        is asked to inspect it rather than have data moved blindly.
        """
        journal = package_transaction.journal_path(self.library)
        if not journal.exists() and not journal.is_symlink():
            return
        try:
            state = package_transaction.parse(self.library, self.character_directory, journal)
            pointer = self.store.get('pointer', 'package', {}) or {}
            committed = pointer.get('id') == state['data']['new_id']
            if committed:
                # Verification needs the document that was actually committed: it is
                # the authority on what this tree must contain.
                package_transaction.finish(state, self.package(state['data']['new_id']))
            else:
                package_transaction.restore(state)
        except (OSError, package_transaction.TransactionError) as error:
            raise ValueError('故事包保存事务未完成，请检查 .package_transaction.json：' + str(error)) from error
        try:
            journal.unlink()
            fsync_directory(self.library)
        except OSError as error:
            raise ValueError('故事包事务已重放，但日志未能删除，请检查权限后重启') from error

    def session_files(self, session):
        folder = self.package(session['revision']).get('folder')
        if not folder:
            raise ValueError('这个旅程绑定的故事包没有目录信息，无法写入笔记')
        return PackageFiles(self.package_directory(folder))

    def list_packages(self):
        result = []
        for path in sorted(self.library.iterdir()):
            if path.name.startswith('.') or not path.is_dir() or path.is_symlink():
                continue
            if (path / 'story.json').exists():
                try:
                    story = PackageFiles(path).read()
                    result.append({'folder':path.name,'title':story['title'],
                                   'active': bool(self.files) and path == self.files.directory})
                except (ValueError, OSError, KeyError):
                    result.append({'folder':path.name,'title':path.name,'error':'文档无效，请检查文件','active':False})
        return result

    def activate_package(self, folder):
        files = PackageFiles(self.package_directory(folder))
        story = files.read()
        char_id = story['character_package_id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', char_id):
            raise ValueError('角色包ID无效')
        charfile = self.character_directory / (char_id+'.json')
        if charfile.exists():
            characters = json.loads(charfile.read_text(encoding='utf-8'))
        else:
            saved = [p for p in self.store.all('package') if p['story']['id']==story['id']]
            if not saved:
                raise ValueError('找不到独立角色包')
            characters = saved[-1]['characters']
        self.validate_package(story, characters)
        previous = self.files
        self.files = files
        try:
            return self.commit_package(story, characters, '启用故事包 '+story['title'])
        except Exception:
            self.files = previous
            raise

    def package(self, revision=None):
        pointer = self.store.get('pointer', 'package')
        revision = revision or (pointer or {}).get('id')
        if not revision:
            raise ValueError('还没有可用的世界：请先创建或采纳一个世界，再开始旅程')
        package = self.store.get('package', revision)
        if not package:
            raise ValueError('故事包版本不存在')
        return package

    def has_world(self):
        """当前是否存在一个可用的世界（被 pointer 指向且包体在）。

        只看两件事：有没有 pointer，以及那个 revision 的包在不在。
        不去扫库里的旧包猜哪个能用 —— 没被指向的都不是当前世界。
        """
        pointer = self.store.get('pointer', 'package') or {}
        revision = pointer.get('id')
        return bool(revision) and bool(self.store.get('package', revision))

    def empty_state(self):
        """正式世界状态（bootstrap 用）：没有世界时明确说没有，而不是造假故事。

        ``world`` 只给公开标识（revision / 标题 / 地点数），不下发任何作者私密内容；
        没有世界时它是 ``None``，并且 ``can_start`` 为 False、带一句可操作原因。
        """
        world = None
        if self.has_world():
            package = self.package()
            world = {'revision': package['id'],
                     'title': package['story'].get('title', ''),
                     'story_id': package['story'].get('id'),
                     'places': len(package['story'].get('locations') or [])}
        return {'world': world, 'packages': self.list_packages(),
                'can_start': world is not None,
                'reason': ('' if world is not None else
                            '还没有可用的世界：请先创建或采纳一个世界，再开始旅程'),
                'library': self.library.name}

    def validate_package(self, story, characters):
        npc_cards.validate(story, characters)
        attributes.validate(story,characters)
        scene_judgment.validate(story, characters)
        if story.get('mechanics',{}).get('calendar'):Calendar.model_validate(story['mechanics']['calendar'])
        for place in story['locations']:
            if place.get('environment'):Environment.model_validate(place['environment'])
        validate_atlas(story)
        local_rules.validate(story,characters)
        rewards_rules.validate(story)
        # Towns carried by this revision are re-validated here, so an imported package
        # cannot smuggle an inconsistent town into a journey (absent key = no-op).
        towns_store.validate_package(story)
        # Same rule for the locked element manifest: an imported package cannot carry a
        # tampered payload hash, a dangling public scope or a broken typed rule. A package
        # without the key is untouched (old packages and old journeys behave as before).
        element_assembly.validate_package(story, characters)
        # Map link: a package may declare which civ-atlas import the player map draws.
        # Absent means "not linked" and stays byte-identical; present means every field is
        # bounded (unknown keys refused, radius numeric and finite, no caller-supplied
        # path) and every location's coordinates must project onto the basemap frame, so a
        # broken link can never reach the player projection.
        play_map.validate_story_map(story)
        # Trait templates are pinned inside the package; if the same ref also appears in
        # the element manifest, both copies must agree. Start profiles reference real
        # places/items/characters/currencies and their entry event must be reachable.
        traits_rules.validate_package(story, characters)
        start_rules.validate_package(story, characters)
        pressure_rules.validate_package(story, characters)
        # 通用冒险行动声明：只有包真的声明了 mechanics.adventure 才检查（老包零影响）。
        # 它同时把 ``adventure:`` 前缀锁给运行时方案：作者静态动作不得占用该命名空间，
        # 否则界面里会出现同 ID 的两个不同动作。
        _reject_reserved_action_ids(story)
        adventure_actions.validate(story, characters)
        # 世界历史：快照在采纳时就已复制进 mechanics.history，这里只查包自身形状与摘要，
        # 不读 store（被删的源记录不能影响已采纳的旅程）。没这个块就是 no-op。
        world_history_store.validate_package_history(story)
        endings_rules.validate_package(story, characters)
        validate_points(story.get('knowledge', []))
        # Keep extension declarations in raw JSON; validate both base schema and references.
        StoryAssembly.model_validate({'story': story, 'characters': characters})
        if story['character_package_id'] != characters['id']:
            raise ValueError('故事包与角色包 ID 不匹配')
        places = {x['id'] for x in story['locations']}
        chars = {x['id'] for x in characters['characters']}
        events = {x['id'] for x in story['events']}
        items = {x['id'] for x in story.get('items', [])}
        for group in (story['locations'], characters['characters'], story['events'], story.get('items', [])):
            if len({x['id'] for x in group}) != len(group):
                raise ValueError('同类元素 ID 不能重复')
        if not places or sum(x['role'] == '主角' for x in characters['characters']) != 1:
            raise ValueError('需要至少一个地点和唯一主角')
        for char in characters['characters']:
            public_voice(char)
            if char.get('location_id') not in places:
                raise ValueError('角色必须绑定有效地点')
            if any(not 0 <= n <= 1 for n in char.get('personality', {}).values()):
                raise ValueError('性格权重必须在 0 到 1 之间')
            bounds = characters.get('generation_constraints', {})
            if char.get('power_level', 0) > bounds.get('max_power_level', 100):
                raise ValueError('角色能力超出故事允许的生成上限')
            if char.get('occupation') and bounds.get('allowed_roles') and char['occupation'] not in bounds['allowed_roles']:
                raise ValueError('角色职业超出生成约束')
        for place in story['locations']:
            if set(place['neighbors']) - places:
                raise ValueError('地点邻接引用无效')
        for event in story['events']:
            if event['location_id'] not in places or set(event['participants']) - chars or set(event['next_events']) - events:
                raise ValueError('事件的地点、参与者或后继事件不存在')
            actions = event.get('actions', [])
            if not actions or not any(a.get('ends_event') for a in actions):
                raise ValueError('每个事件需要操作和明确结束出口')
            if len({a['id'] for a in actions}) != len(actions):
                raise ValueError('事件操作 ID 重复')
            for action in actions:
                validate_cues(action.get('narrative_cues', {}))
                # 作者公开的意图别名：有界、去重、非空；它是玩家可见文本，不替作者把关内容。
                free_actions.validate_action_aliases(action)
                check = action.get('check')
                if check and not (0 <= check['difficulty'] <= 1):
                    raise ValueError('检定难度应在 0 到 1 之间')
                for branch in ('effects', 'success', 'failure'):
                    for effect in action.get(branch, []):
                        if effect.get('op') not in ('flag', 'take', 'fact', 'rumor', 'status', 'resource', 'information','health'):
                            raise ValueError('未支持的状态操作')
                        if effect['op'] == 'take' and effect['id'] not in items:
                            raise ValueError('物品不存在')
                        if effect['op']=='health' and (type(effect.get('delta')) is not int or not -10000<=effect['delta']<=10000):
                            raise ValueError('血量变化需要-10000至10000整数delta')
                        if effect['op'] == 'rumor' and effect.get('character') not in chars:
                            raise ValueError('传闻角色不存在')
        for item in story.get('items', []):
            if item.get('location_id') not in places:
                raise ValueError('物品必须绑定有效地点')
        for raw in story.get('elements', []):
            element = Element.model_validate(raw)
            if element.location_id and element.location_id not in places:
                raise ValueError('元素可见性地点不存在')
            if set(element.known_by) - (chars | {'player'}):
                raise ValueError('元素可见性受众不存在')
            for field in element.public_fields:
                if field not in element.data or not isinstance(element.data[field], (str, int, float, bool)):
                    raise ValueError('公开字段必须为有效的单个文本或数值')
        scenes = story.get('major_scenes', [])
        if scenes:
            scene_ids = {x['id'] for x in scenes}
            if len(scene_ids) != len(scenes):
                raise ValueError('主要场景 ID 重复')
            for scene in scenes:
                if set(scene['location_ids']) - places or not scene['location_ids']:
                    raise ValueError('主要场景需绑定有效地点')
            for event in story['events']:
                if event.get('major_scene_id'):
                    scene = next((x for x in scenes if x['id'] == event['major_scene_id']), None)
                    if not scene or event['location_id'] not in scene['location_ids']:
                        raise ValueError('事件不属于指定主要场景')

    def commit_package(self, story, characters, note, approved_draft=None):
        story,characters=attributes.upgrade(story,characters)
        self.validate_package(story, characters)
        previous = self.files
        current = self.package() if self.store.get('pointer','package') else None
        if current and current['story']['id'] != story['id']:
            matching = [p for p in self.store.all('package') if p['story']['id']==story['id']]
            if matching:
                self.files = PackageFiles(self.package_directory(matching[-1].get('folder','玄陆')))
            elif self.files.directory == self.package_directory(current.get('folder','玄陆')):
                self.files = PackageFiles(self.package_directory('导入_'+uid()))
        if self.files is None:
            # 首次创建世界：库里还没有 pointer，目录名由这次提交自己认领。
            # 不沿用旧预制目录名，也不在启动时预先建好。
            folder = 'world_' + revision_folder_slug(story.get('id'))
            directory = self.package_directory(folder)
            self.files = PackageFiles(directory)
        target = self.files.directory
        if target.parent.resolve() != self.library.resolve():
            self.files = previous
            raise ValueError('故事包目录必须位于 StoryPackage 内')
        char_id = characters['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', char_id):
            self.files = previous
            raise ValueError('角色包ID无效')
        revision = uid()
        transaction = uid()
        stage = target.parent / ('.' + target.name + '.pending_' + transaction)
        backup = target.parent / ('.' + target.name + '.backup_' + transaction)
        char_path = self.character_directory / (char_id + '.json')
        char_backup = self.character_directory / ('.' + char_id + '.backup_' + transaction + '.json')
        journal = package_transaction.journal_path(self.library)
        data = {'version': package_transaction.VERSION, 'transaction': transaction,
                'target': target.name, 'stage': stage.name, 'backup': backup.name,
                'target_existed': target.exists(), 'new_id': revision, 'character_id': char_id,
                'character_file': char_path.name, 'character_backup': char_backup.name,
                'character_existed': char_path.exists(), 'phase': 'prepared'}
        try:
            # Exclusive creation: two concurrent commits cannot both believe they own
            # the journal, and a leftover journal must be replayed before a new one.
            package_transaction.write_exclusive(journal, package_transaction.encode(data))
        except FileExistsError:
            self.files = previous
            raise ValueError('已有故事包保存事务待恢复，请重启应用后重试')
        except OSError:
            self.files = previous
            raise
        state = {'data': data, 'target': target, 'stage': stage, 'backup': backup,
                 'char_path': char_path, 'char_backup': char_backup}
        try:
            if target.is_symlink():
                raise ValueError('故事包目录不支持符号链接')
            if target.exists():
                # Refuse linked trees: the staged copy must not be able to write back
                # into a file elsewhere on disk through a preserved link.
                package_transaction.assert_no_symlinks(target)
                shutil.copytree(target, stage, symlinks=False)
            else:
                stage.mkdir(parents=True, exist_ok=False)
            package_transaction.fsync_directory(target.parent)
            PackageFiles(stage).write(story)
            story = PackageFiles(stage).read()
            self.validate_package(story, characters)
            data = state['data'] = package_transaction.mark(journal, data, 'staged')
            package = {'id': revision, 'created': now(), 'note': note, 'story': story,
                       'characters': characters, 'folder':target.name}
            records = [('package', revision, package),
                       ('pointer', 'package', {'id': revision, 'folder':target.name})]
            data = state['data'] = package_transaction.mark(journal, data, 'characters')
            if char_path.exists():
                if char_path.is_symlink():
                    raise ValueError('角色包文件不能是符号链接')
                # Copy by bytes and publish with one rename: a crash mid-copy can only
                # leave a stray temporary file, never a truncated backup that a later
                # restore would move over the still-complete live document.
                package_transaction.write_atomic_bytes(
                    char_backup, char_path.read_bytes())
            else:
                char_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_text(char_path, json.dumps(characters, ensure_ascii=False, indent=2))
            if target.exists():
                target.rename(backup)
                package_transaction.fsync_directory(target.parent)
            stage.rename(target)
            package_transaction.fsync_directory(target.parent)
        except BaseException as error:
            # One rollback path for ordinary exceptions and interrupts alike. This is a
            # *same-process* cleanup; it is not a simulation of the process dying.
            self.files = previous
            state['data'] = data
            self._rollback_package_commit(state)
            raise error if isinstance(error, Exception) else RuntimeError('故事包提交被中断，已回滚到提交前版本')
        try:
            if approved_draft is not None:
                approved = {**approved_draft, 'status': 'approved', 'revision': revision}
                records.append(('draft', approved['id'], approved))
            self.store.put_many(records)
        except Exception as error:
            # Hand back everything the commit changed, including the in-memory draft
            # flag, so a failed save never leaves an approved candidate behind.
            self.files = previous
            state['data'] = data
            self._rollback_package_commit(state)
            raise error
        if approved_draft is not None:
            approved_draft.update(status='approved', revision=revision)
        self.files = PackageFiles(target)
        # From the committed pointer on, the revision is the truth: every later failure
        # is "saved but not cleaned up" and is completed on the next start, never undone.
        try:
            data = state['data'] = package_transaction.mark(journal, data, 'committed')
            package_transaction.finish(state, package)
            package_transaction.remove(journal)
            fsync_directory(self.library)
        except (OSError, package_transaction.TransactionError) as error:
            raise ValueError('故事包已保存，但旧版本清理未完成；重启应用后会继续清理') from error
        return revision

    def _rollback_package_commit(self, state):
        """Put the previous package back; safe to repeat and to interrupt.

        The journal is retired only after the restore succeeded: if the restore itself
        failed, the record stays so the next start can replay it instead of leaving a
        half-restored package that nobody knows about.
        """
        package_transaction.restore(state)
        package_transaction.remove(package_transaction.journal_path(self.library))
        fsync_directory(self.library)

    def reload_documents(self):
        story = self.files.read()
        current = self.package()
        char_id=story['character_package_id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',char_id):raise ValueError('角色包ID无效')
        charfile=self.character_directory/(char_id+'.json')
        chars=json.loads(charfile.read_text(encoding='utf-8-sig')) if charfile.exists() else current['characters']
        story,chars=attributes.upgrade(story,chars,legacy='attributes' not in current['story'].get('mechanics',{}))
        self.validate_package(story, chars)
        if story == current['story'] and chars==current['characters']:
            return current['id']
        return self.commit_package(story, chars, '从 StoryPackage 文件夹读取文档')

    def new_session(self, title, mode, profile_id=None):
        """Create one journey.

        Order is deliberate: the whole candidate snapshot is built (including the start
        profile's engine-side grants) and only then is time advanced and the first event
        entered. Applying the profile after ``advance``/``enter`` would run a schedule or
        a one-shot effect against the OLD opening and then overwrite it.
        """
        # 没有世界时直接拒，不去 reload/构造隐藏故事：告诉用户可以做什么。
        if not self.files:
            raise ValueError('还没有可用的世界：请先创建或采纳一个世界，再开始旅程')
        self.reload_documents()
        p = self.package()
        hero = next(c for c in p['characters']['characters'] if c['role'] == '主角')
        s = {'id': uid(), 'title': title, 'created': now(), 'revision': p['id'], 'mode': mode,
             'hero': hero['id'], 'location': hero['location_id'], 'time': 8,
             'explored': [hero['location_id']], 'inventory': [], 'flags': {}, 'completed': [],
             'characters': {c['id']: {'location': c['location_id'], 'status': copy.deepcopy(c.get('state', {}))} for c in p['characters']['characters']},
             'facts': [], 'beliefs': [], 'heard': [], 'seed': uid(), 'checks': [], 'active': None,
             'archives': [], 'usage': [], 'turn_index': 0, 'decisions': []}
        # An empty reward ledger when configured, so an event's `before` snapshot already
        # carries zeros and a rollback lands on the same shape. Unconfigured stays bare.
        rewards_rules.ensure(s, p['story'])
        # Start profile runs on the candidate state, before any clock work. Any refusal
        # (unknown currency/item/template/character, entry event unreachable) raises and
        # nothing has been saved yet, so the failure is a zero write.
        start_cfg = start_rules.config(p['story'])
        profile = start_rules.resolve(start_cfg, profile_id)
        start_rules.apply(s, p['story'], p['characters'], profile)
        # One clock for everything: local resources/schedules AND story pressure.
        # `advance` is the only entry point, so the two cannot drift apart.
        pressure_rules.advance(s, p['story'], p['characters'], 0, effects=self.effects)
        self.enter(s)
        self.store.save_session(s)
        return s

    def candidates(self, s):
        nodes = self.package(s['revision'])['story']['events']
        incoming = {x['id']: [n['id'] for n in nodes if x['id'] in n['next_events']] for x in nodes}
        return [e for e in nodes if e['id'] not in s['completed'] and e['location_id'] == s['location']
                and (not incoming[e['id']] or any(x in s['completed'] for x in incoming[e['id']]))
                and all(s['flags'].get(k, False) == v for k, v in e.get('entry_flags', {}).items())
                and e.get('time_min', 0) <= s['time'] <= e.get('time_max', 10**9)]

    def snapshot(self, s):
        return copy.deepcopy({k: v for k, v in s.items() if k not in ('active', 'archives', 'state_version')})

    def enter(self, s):
        possible = self.candidates(s)
        # A start profile names a specific entry event. It is honoured only while that
        # event has never been played and is still eligible; afterwards normal queueing
        # resumes, so the override cannot be reused to replay a finished opening.
        start = s.get('start') or {}
        forced = s.pop('forced_entry', None)
        entry = forced or start.get('entry_event')
        chosen = None
        if entry and entry not in s['completed'] and (forced or not start.get('entry_consumed')):
            chosen = next((e for e in possible if e['id'] == entry), None)
            if chosen is not None and not forced:
                start['entry_consumed'] = True
        if chosen is None:
            chosen = possible[0] if possible else None
        if chosen is not None:
            event = chosen
            story = self.package(s['revision'])['story']
            # Authored scene entrances, not model-created teleportation.
            for cid, place in story.get('mechanics', {}).get('scene_judgment', {}).get('scene_cast', {}).get(event['id'], {}).items():
                s['characters'][cid]['location'] = place
            scene_id = event.get('major_scene_id', event['location_id'])
            scene = next((x for x in story.get('major_scenes', []) if x['id'] == scene_id), None)
            title = scene['title'] if scene else next(l['name'] for l in story['locations'] if l['id'] == event['location_id'])
            prefs = self.store.get('settings', 'preferences', {})
            groups = self.conversations(s)
            count = len(groups[-1]['turns']) if groups else 0
            changed = s.get('last_scene_id', (s.get('conversation') or {}).get('scene_id')) != scene_id
            split = changed and (prefs.get('conversation_mode', 'chapter') == 'scene'
                                 or count >= prefs.get('chapter_turns', 40)
                                 or (scene or {}).get('force_new_conversation', False))
            if not s.get('conversation') or split:
                s['conversation'] = {'id': uid(), 'scene_id': scene_id, 'title': title}
            s['last_scene_id'] = scene_id
            s['active'] = {'id': uid(), 'node': event['id'], 'title': event['title'],
                           'key': rewards_rules.new_branch_key(s, event['id']),
                           'conversation': copy.deepcopy(s['conversation']),
                           'before': self.snapshot(s), 'turns': [], 'actions_done': []}

    def conversations(self, s):
        groups = []
        for event in s['archives'] + ([s['active']] if s['active'] else []):
            descriptor = event.get('conversation', {'id': event['id'], 'scene_id': event['node'], 'title': event['title']})
            group = next((g for g in groups if g['id'] == descriptor['id']), None)
            if group is None:
                group = {**descriptor, 'turns': [], 'events': []}
                groups.append(group)
            group['turns'].extend(event['turns'])
            group['events'].append(event['title'])
        return groups

    def node(self, s):
        return next(e for e in self.package(s['revision'])['story']['events'] if e['id'] == s['active']['node'])

    def project_elements(self, s, audience):
        result = []
        p = self.package(s['revision'])
        for element in p['story'].get('elements', []):
            if element.get('location_id') and element['location_id'] != s['location']:
                continue
            if element.get('reveal_flag') and not s['flags'].get(element['reveal_flag']):
                continue
            if element.get('known_by') and audience not in element['known_by']:
                continue
            # Empty field lists mean no disclosure; never fall back to all fields.
            data = {k: element['data'][k] for k in element['public_fields'] if k in element['data']}
            if data:
                result.append(data)
        return result

    def world_history(self, s, story, audience):
        """本旅程**绑定的那一版**包里已采纳的世界历史，按受众白名单投影。

        三个不变量：

        * 只读 ``story``（= ``package(session['revision'])['story']``），绝不按
          ``snapshot_id`` 回查 store：源记录被删不能改变已采纳的旅程。
        * 受众由调用方给（NPC 用它自己的 id），逐条按作者的 ``known_by`` / 地点 / 标记过滤。
        * 条目数与字符数都有上限；空结果返回 ``None``，调用方就不加 key（旧包一字不变）。
        """
        rows = world_history_store.package_history_public(story, s, audience)
        if not rows:
            return None
        items = []
        for row in rows[:WORLD_HISTORY_MAX_ITEMS]:
            entry = {key: value for key, value in row.items()
                     if key in WORLD_HISTORY_FIELDS and value is not None}
            if entry:
                items.append(entry)
        while items and chars({'items': items}) > WORLD_HISTORY_MAX_CHARS:
            items.pop()
        if not items:
            return None
        return {'basis': '作者为这个世界采纳的历史设定：只含已公开的条目，'
                         '不代表未来的结局，也不代表角色一定知道',
                'items': items}

    def memories(self, s, audience, query, k):
        records = s['heard'] if audience == 'player' else [r for r in s['beliefs'] if r['character'] == audience]
        terms = set(vector(query))
        records = [r for r in records if terms & set(vector(r['text']))]
        def score(r):
            overlap = len(set(query) & set(r['text'])) / max(1, len(set(query)))
            return overlap + r.get('intensity', 0.4) + 1 / (1 + max(0, s['time'] - r['time']))
        return sorted(records, key=lambda r:(-score(r), str(r.get('id','')),r['text']))[:k]

    def context(self, s, audience, query, preferences):
        p = self.package(s['revision'])
        location = next(l for l in p['story']['locations'] if l['id'] == s['location'])
        # The locked element manifest is projected from this viewpoint. An NPC reads their
        # own place and knowledge; a character viewpoint below replaces this with its own.
        viewpoint = s
        visible_characters = []
        for c in p['characters']['characters']:
            if s['characters'][c['id']]['location'] == s['location']:
                visible_characters.append({'id': c['id'], 'name': c.get('public_name', c['name']), 'appearance': c.get('appearance', '')})
        result = {'location': location['name'], 'description': location.get('public_description', location['description']),
                  'characters': visible_characters, 'elements': self.project_elements(s, audience),
                  'memories': [{**{k:r[k] for k in ('id','text','source','speaker','kind','distortion','source_fact','certainty') if k in r}, 'freshness': '清晰' if s['time'] - r['time'] < 12 else '模糊'} for r in self.memories(s, audience, query, preferences['memory_k'])],
                  'history': s['active']['turns'][-preferences['history_turns']:] if s['active'] else [],
                  'last_summary': s['archives'][-1]['summary'] if s['archives'] else '', 'input': query,
                  'mode': s['mode']}
        groups = self.conversations(s)
        if groups:
            # Tag old prose with its real event location instead of implying it
            # all happened in the current scene. Never alter stored player text.
            tagged = []
            events = s['archives'] + ([s['active']] if s['active'] else [])
            current_id = groups[-1]['id']
            for event in events:
                before = event.get('before', {})
                loc_id = before.get('location')
                loc_name = next((l['name'] for l in p['story']['locations'] if l['id'] == loc_id), '此前地点未记录')
                for turn in event['turns']:
                    tagged.append({**turn, 'location': loc_name, 'event': event['title'],
                                   '_conversation': event.get('conversation', {}).get('id', event['id'])})
            current_turns = [t for t in tagged if t['_conversation'] == current_id]
            selected, stage_summary, stage = stage_history(
                [{k:v for k,v in t.items() if k != '_conversation'} for t in current_turns],preferences)
            result['history'] = selected
            # Settlement of the last closed event, then the fixed stage excerpt.
            result['last_summary'] = with_stage(result['last_summary'], stage_summary)
            # Retrieve a few exact older exchanges, including player statements.
            # These are evidence of speech, never new objective facts.
            result['recalled_dialogue'] = []
            if audience == 'player' and preferences.get('recall_enabled', True):
                records = dialogue_records(s, p)
                recent = [r for r in records if r['conversation_id'] == current_id]
                recent = recent[-len(selected):] if selected else []
                result['recalled_dialogue'] = self.recall.search(s['id'], query, records,
                    exclude=[r['source_id'] for r in recent], k=preferences['memory_k'],
                    threshold=preferences.get('recall_threshold', 0.12))
            # Stage excerpt changes only on a deterministic stage boundary.
            current_scene = next((x for x in p['story'].get('major_scenes', []) if x['id'] == s.get('last_scene_id')), None)
            result['scene'] = current_scene['title'] if current_scene else location['name']
        result['current_time'] = s['time']
        # 世界历史：只从本 session revision 的包里读，按该受众白名单过滤；空就不加 key。
        # 它与上面的 ``history``（对话轮次）是两个不同的键，后者一字不动。
        chronicle = self.world_history(s, p['story'], audience)
        if chronicle is not None:
            result['current_world_history'] = chronicle
        if audience=='player':
            result['local_state']=local_rules.view(s,p['story'])
            hero=next(c for c in p['characters']['characters'] if c['id']==s['hero'])
            vals=attributes.values(hero.get('attributes'),legacy=set(hero.get('attributes',{}))!=set(attributes.AXES))
            result['player_abilities']={'values':vals,'health':attributes.health(hero,s['characters'][s['hero']]['status']),
                'keywords':self.attribute_vectors.search(p['story'].get('mechanics',{}).get('attributes',attributes.specification()),vals,query,3)}
            # Authoritative holdings for this viewpoint. Absent config means no key at
            # all, so an untouched package produces the identical prompt as before.
            holding = rewards_rules.public_state(s, p['story'], 'player')
            if holding is not None:
                result['current_rewards'] = holding
        if s['active']:
            result['cast'] = cast_projection(p,s,self.node(s)['participants'],audience)
            for cast in result['cast']:
                c=next(c for c in p['characters']['characters'] if c['id']==cast['id'])
                vals=attributes.values(c.get('attributes'),legacy=set(c.get('attributes',{}))!=set(attributes.AXES))
                cast['attribute_keywords']=self.attribute_vectors.search(p['story'].get('mechanics',{}).get('attributes',attributes.specification()),vals,query,2)
        surface = self.surface(s)
        result['current_state'] = surface['status']
        result['current_daytime'] = surface['daytime']
        result['current_inventory'] = surface['inventory']
        result['current_event'] = surface['event']
        result['current_anchor'] = {
            'location': location['name'], 'scene': result.get('scene', location['name']),
            'daytime': surface['daytime'], 'inventory': surface['inventory'],
            'event': surface['event'],
            'confirmed_records': [r['text'] for r in s['heard'] if r.get('distortion') == 0][-8:],
        }
        result['knowledge'] = retrieve(p['story'], query + ' ' + location['name'], audience,
                                       s['location'], s['flags'])
        # One bounded public town summary for the *current* location only: never the
        # whole town, never its secrets, and never a place this journey has not reached.
        town = towns_store.context_snippet(p['story'], s['location'])
        if town and any(row['location_id'] == s['location']
                        for row in towns_store.story_towns(p['story'], s['revision'], s)):
            result['town_summary'] = town
        notes = notebook(s) if audience == 'player' else []
        relevant = [n for n in notes if any(k in query for k in n['keywords'])]
        # Exact evidence deduplication only; never rewrite negation or uncertain claims.
        already = '\n'.join(t['reply'] for t in result['history']) + '\n' + result['last_summary']
        # Engine-confirmed records first: they are the only notes the rules engine
        # verified itself. Model-derived prose fills the remaining slots and keeps
        # its unverified status label.
        ordered = ([n for n in relevant if n.get('origin') == 'confirmed'][-2:] +
                   [n for n in relevant if n.get('origin') != 'confirmed'][::-1])
        unique = []
        for n in ordered:
            summary = n['summary']
            if summary in already or any(summary == x['summary'] for x in unique):
                continue
            unique.append({'summary': summary, 'status': n['status']})
            if len(unique) == 3:
                break
        result['dialogue_knowledge'] = unique
        if audience != 'player':
            c = next((c for c in p['characters']['characters'] if c['id'] == audience), None)
            if c is None:
                raise ValueError('角色不存在')
            result['self'] = {k: c.get(k) for k in ('name', 'traits', 'personality')}
            result['self']['personality'] = {**c.get('personality',{}), **s.get('development',{}).get(audience,{}).get('personality',{})}
            # Player conversations and summaries may contain facts unknown to this NPC.
            result['history'] = []
            result['last_summary'] = ''
            result['recalled_dialogue'] = []
            # A character viewpoint cannot inherit the player's possessions or
            # private confirmed records. NPC local perception is explicit.
            npc_location = s['characters'][audience]['location']
            npc_place = next(l for l in p['story']['locations'] if l['id']==npc_location)
            result.update(location=npc_place['name'],description=npc_place.get('public_description',npc_place['description']),
                          scene=npc_place['name'],current_inventory=[],current_event=None,dialogue_knowledge=[],
                          current_state=copy.deepcopy(s['characters'][audience]['status']))
            result['characters']=[{'id':x['id'],'name':x.get('public_name',x['name']),'appearance':x.get('appearance','')}
                                  for x in p['characters']['characters'] if s['characters'][x['id']]['location']==npc_location]
            viewpoint=copy.deepcopy(s);viewpoint['location']=npc_location
            result['elements']=self.project_elements(viewpoint,audience)
            result['knowledge']=retrieve(p['story'],query+' '+npc_place['name'],audience,npc_location,s['flags'])
            result['current_anchor']={'location':npc_place['name'],'daytime':surface['daytime'],
                                      'inventory':[],'inventory_complete':False,'confirmed_records':[]}
            result['cast'] = cast_projection(p, viewpoint, [audience], audience)
        cards = npc_cards.context(p, viewpoint, audience,
                                  [audience] if audience != 'player' else
                                  self.node(s)['participants'] if s['active'] else [])
        if cards:
            result['npc_cards'] = cards
        # Locked element manifest: projection only, never a library lookup. The journey
        # reads the snapshot inside its own package revision, so a library update or a
        # deletion cannot add element types to a running story.
        projected = element_assembly.context_elements(p['story'], audience, viewpoint)
        if projected is not None:
            result['current_elements'] = projected
        # Traits and known warnings share the SAME character budget as everything else:
        # they are handed the remaining room, then trimmed by the normal path below.
        # Both return None when the package declares nothing, so old prompts are unchanged.
        # `viewpoint` is used so an NPC only sees traits of people present at ITS location.
        remaining = budget_for(preferences) - chars(result)
        traits_block = traits_rules.context(p['story'], viewpoint, audience,
                                            budget=remaining,
                                            characters=p['characters'])
        if traits_block is not None:
            result['current_traits'] = traits_block
        warning_block = pressure_rules.context(s, p['story'], audience)
        if warning_block is not None:
            # Only what this viewpoint already knows: never stage counts or thresholds.
            result['current_pressure'] = warning_block
        anchor_place = location if audience == 'player' else npc_place
        result['current_anchor'].update(state_anchor(s, anchor_place, result.get('scene', anchor_place['name']), result['characters']))
        result['current_anchor'].setdefault('inventory_complete', True)
        if audience == 'player' and result.get('current_rewards'):
            # The anchor promises a complete list of confirmed holdings, so reward
            # instances join it by public label only; unidentified items stay a label.
            labels = [x['label'] for x in result['current_rewards']['items']]
            result['current_anchor']['inventory'] = list(result['current_anchor']['inventory']) + labels
            result['current_anchor']['inventory_sources'] = '物品清单含世界物品与本次旅程获得的物品实例；未鉴定物品只显示可观察标签'
        if audience=='player':
            result['geography']=local_environment(p['story'],s)
            if result['geography'].get('sun'):
                result['current_anchor']['solar']=result['geography']['sun']
                result['current_anchor']['clock']['calendar']='类地365日历；solar给出年内日与统一游戏UTC偏移，不自动切换时区'
                result['current_anchor']['unspecified']='日出日落按solar近似值；房间、天气与地形遮挡未确认'
        # Remove oldest contextual material first, never truncate malformed JSON.
        budget = budget_for(preferences)
        trim_context(result, budget)
        # The element summary shares the same budget. Whole entries (or a whole fact list)
        # are dropped: never a sliced sentence, because cutting a clause can turn「不能」
        # into「能」. An absent manifest never reaches this block.
        while result.get('current_elements') and chars(result) > budget:
            items = result['current_elements'].get('items') or []
            if len(items) > 1:
                result['current_elements']['items'] = items[:-1]
            elif items and items[-1].get('facts'):
                items[-1].pop('facts')
            else:
                result.pop('current_elements', None)
        if chars(result) > budget:
            raise ValueError('事件基础上下文超出预算，请缩短输入或提高设置中的预算')
        return result

    def resolved_rewards(self, result, cfg=None):
        """Model-facing result: keep only what may be narrated to the player.

        `reward_audit` would carry before/after numbers, template IDs and hidden
        enchantment levels; that is author-side bookkeeping and must never reach
        `context['resolved_action']` or a character viewpoint.
        """
        public = copy.deepcopy(result)
        public.pop('reward_audit', None)
        return public

    def effects(self, s, effects, source, reward_claims=None):
        """Apply one batch of state effects, atomically when rewards are involved.

        A reward batch plus legacy effects must not leave the caller's candidate
        session half-updated when a later effect fails, so the mixed path works on a
        deep copy and commits only after every operation succeeded. Batches without
        reward claims keep the original in-place behaviour unchanged.
        """
        p = self.package(s['revision'])
        cfg = rewards_rules.rules(p['story'])
        claims = list(reward_claims or [])
        for effect in effects:
            if effect.get('op') == 'reward':
                claims.append({'entry': effect.get('entry')})
        if claims and cfg is None:
            raise ValueError('奖励效果需要先配置 mechanics.rewards')
        work = copy.deepcopy(s) if claims else s
        self._apply_effects(work, effects, source, p)
        audits = []
        if claims:
            # Flags set by this very action are visible to ability prerequisites.
            cfg = rewards_rules.ensure(work, p['story'])
            applied, audits = rewards_rules.apply(work, cfg, claims, source)
            work['rewards'] = applied
            s.clear()
            s.update(work)
        return audits

    def _apply_effects(self, s, effects, source, p):
        for effect in effects:
            op = effect['op']
            if op=='health':
                hero=next(c for c in p['characters']['characters'] if c['id']==s['hero'])
                status=s['characters'][s['hero']]['status'];h=attributes.health(hero,status)
                current=max(0,min(h['maximum'],h['current']+effect['delta']))
                status['damage']=h['maximum']-current
                s['facts'].append({'id':uid(),'text':f'血量{h["current"]}→{current}','time':s['time'],'source':source})
            elif op == 'flag':
                s['flags'][effect['id']] = bool(effect['value'])
            elif op == 'take':
                item = next(i for i in p['story']['items'] if i['id'] == effect['id'])
                if item['location_id'] != s['location'] or item['id'] in s['inventory']:
                    raise ValueError('无法获得不在现场或已经持有的物品')
                s['inventory'].append(item['id'])
                s['facts'].append({'id': uid(), 'text': '获得' + item['name'], 'time': s['time'], 'source': source})
            elif op == 'resource':
                cfg=local_rules.ensure(s,p['story'])
                local_rules.change_resource(s,cfg,effect['id'],effect['delta'],source)
            elif op == 'reward':
                # Collected and applied as one validated batch by `effects`.
                continue
            elif op == 'information':
                record={'id':uid(),'text':effect['text'],'time':s['time'],'source':source,
                        'distortion':0 if effect.get('confirmed',False) else 1,'intensity':.5}
                if effect.get('confirmed',False):s['facts'].append(record)
                for audience in effect['known_by']:
                    if audience=='player':s['heard'].append({**record,'id':uid()})
                    else:s['beliefs'].append({**record,'id':uid(),'character':audience,'kind':'information'})
            elif op == 'status':
                status = s['characters'][s['hero']]['status']
                status[effect['id']] = max(0, min(1, status.get(effect['id'], 0) + effect['delta']))
            elif op == 'fact':
                fact = {'id': uid(), 'text': effect['text'], 'time': s['time'], 'source': source}
                s['facts'].append(fact)
                if effect.get('visible'):
                    s['heard'].append({**fact, 'source_fact': fact['id'], 'distortion': 0, 'intensity': 0.6})
            elif op == 'rumor':
                fact = {'id': uid(), 'text': effect['truth'], 'time': s['time'], 'source': source}
                s['facts'].append(fact)
                # Both versions derive from the same fact, with an explicit transform.
                text = fact['text']
                if effect.get('transform') == 'number_scale':
                    factor = effect.get('factor', 2)
                    text = re.sub(r'\d+', lambda m: str(round(int(m[0]) * factor)), text)
                elif effect.get('transform') == 'partial':
                    text = text.split('；')[0]
                belief = {'id': uid(), 'source_fact': fact['id'], 'text': text, 'character': effect['character'],
                          'time': s['time'], 'distortion': 0.5, 'source': effect.get('source', '转述'), 'intensity': 0.8}
                s['beliefs'].append(belief)
                s['heard'].append({**belief, 'id': uid(), 'speaker': effect['character']})
            else:
                raise ValueError('非法状态变更')

    def prepare_turn(self, s, request):
        package=self.package(s['revision'])
        cfg=local_rules.ensure(s,package['story'])
        if not s['active']:
            self.enter(s)
        if not s['active']:
            # 没有可进入的事件时，通用行动走各自的专用路径（休息=/wait、旅行=move），
            # 而不是为了兼容伪造一个故事事件。这里给一句可操作的话，而非死按钮。
            raise ValueError('当前地点没有可进入的事件：休息请用等待，旅行请用地图移动')
        node = self.node(s)
        # 先解析并校验，再产生任何副作用：不合法时既没有 communicate，也没有 charge/effects。
        plan = None
        action = None
        duration = cfg.turn_hours
        if request.action_id:
            if s['mode'] == 'observer' or (s['mode'] == 'mixed' and not node.get('player_enters', False)):
                raise ValueError('旁观阶段可补述或注解，不能直接操作人物和物品')
            action, plan, duration = self.resolve_action(s, node, request, package['story'])
        listeners=local_rules.communicate(s,node,request,cfg.memory_limit)
        if s['mode'] == 'mixed' and node.get('player_enters', False):
            s['characters'][s['hero']]['location'] = s['location']
        result = {'ends': False, 'outcome': '继续对话', 'voice': ''}
        result['input_channel']=request.channel
        result['listeners']=listeners
        if request.action_id:
            success = True
            local_rules.charge(s,package['story'],action,node['id']+':'+action['id'])
            if action.get('check'):
                check = action['check']
                hero = next(c for c in self.package(s['revision'])['characters']['characters'] if c['id'] == s['hero'])
                axis=attributes.ALIASES.get(check['attribute'],check['attribute'])
                vals=attributes.values(hero.get('attributes'),legacy=set(hero.get('attributes',{}))!=set(attributes.AXES))
                ability=vals[axis]/100 if axis in vals else hero.get('attributes',{}).get(check['attribute'],.5)
                fatigue = s['characters'][s['hero']]['status'].get('疲劳', 0)
                seed = f"{s['seed']}:{node['id']}:{action['id']}"
                audit = resolve_check(seed,check['attribute'],ability,check['difficulty'],fatigue)
                success = audit['success']
                audit['ability_defaulted'] = check['attribute'] not in hero.get('attributes', {})
                s['checks'].append(audit)
            # Declared branch rewards and reward effects join one batch so a failure
            # anywhere leaves neither half the effects nor half the rewards applied.
            declared = action.get('rewards') or {}
            claims = [{'entry': str(x)} for x in declared.get('success' if success else 'failure', [])]
            audits = self.effects(s, action.get('effects', []) + action.get('success' if success else 'failure', []),
                                  node['id'] + ':' + action['id'], claims)
            public = rewards_rules.public_result(rewards_rules.rules(package['story']), audits, s)
            if public:
                result['rewards'] = public
            if audits:
                # Author-side audit trail (before/after, template, hidden levels). It is
                # stripped from `resolved_action` before the model or an NPC sees it.
                result['reward_audit'] = audits
            result.update(ends=action.get('ends_event', False), outcome=action.get('success_text' if success else 'failure_text', action['label']))
            result['narrative'] = outcome_cues(action,success,bool(action.get('check')))
            # 可重复类（休息/旅行）不记 ``actions_done``：时间推进本身可以反复做。其余
            # （动态的观察/调查/交涉/取物）与既有静态动作同语义：当前事件内只做一次，
            # 回滚回事件起点后可重做；奖励靠既有 ``grant_id`` 幂等，不另开账本。
            if plan is None or plan['kind'] not in adventure_actions.REPEATABLE:
                s['active']['actions_done'].append(action['id'])
        npc_cards.remember_action(package, s, node, action, result)
        # Deterministic personality response, biased by current state and beliefs.
        for cid in node['participants']:
            if cid == s['hero']:
                continue
            if s['characters'][cid]['location'] != s['location']:
                continue
            c = next(c for c in self.package(s['revision'])['characters']['characters'] if c['id'] == cid)
            growth = s.get('development',{}).get(cid,{})
            weights = {**c.get('personality', {}),**growth.get('personality',{})}
            if weights:
                tendency = max(weights, key=lambda t: weights[t] + (s['characters'][cid]['status'].get('警惕', 0) * 0.3 if t == '谨慎' else 0))
                belief = next((b for b in reversed(s['beliefs']) if b['character'] == cid and b.get('kind')!='statement'), None)
                s['decisions'].append({'character': cid, 'tendency': tendency, 'weights': weights, 'state': copy.deepcopy(s['characters'][cid]['status']), 'source_belief': belief['id'] if belief else None})
                expression=attributes.performance(c)
                choices=expression['social_actions']
                offset=int(hashlib.sha256(cid.encode()).hexdigest()[:8],16)
                action=choices[(s['turn_index']+offset)%len(choices)]
                reaction=action+'；依据本人的动机和语气回应，别复制其他角色句式。'
                trust=growth.get('relationships',{}).get(s['hero'],{}).get('trust')
                if trust is not None:
                    reaction += ' 愿意耐心听，但保留自身立场。' if trust>=0.6 else ' 保留距离，不立刻答应。'
                emotion=''
                if growth.get('emotion_expires_after_turn',-1)>=s['turn_index']+1 and growth.get('emotion'):
                    strongest=max(growth['emotion'],key=growth['emotion'].get)
                    reaction+=' 暂时表现出'+strongest+'，不必念出情绪名称。'
                    emotion=strongest
                if belief:
                    reaction += ' 有未核实信念不等于真相；只能引用上下文已公开的消息。'
                    s['characters'][cid]['status']['警惕'] = min(1, s['characters'][cid]['status'].get('警惕', 0) + 0.1)
                result.setdefault('reactions', []).append({'character':cid,'cue':reaction})
                # Offline narration gets the same decision as structured public
                # behaviour, never the internal instruction text above.
                result.setdefault('performances', []).append({
                    'character': cid, 'public_name': c.get('public_name') or c['name'],
                    'action': action, 'emotion': emotion,
                    'stance': 'guarded' if trust is not None and trust < 0.6 else 'open' if trust is not None else 'neutral',
                    'unverified_claim': bool(belief)})
        # Inner feelings remain optional prose, not a repeated required line.
        for branch in node.get('special_branches', []):
            if branch.get('item_id') in s['inventory'] or (branch.get('memory_text') and any(branch['memory_text'] in m['text'] for m in s['heard'])):
                result['special_dialogue'] = branch['text']
                break
        # The clock and the story pressure share one entry point: `pressure_rules.advance`
        # calls local_rules.advance first, then evaluates stages against the same time.
        pressure_rules.advance(s, package['story'], package['characters'], duration,
                               effects=self.effects)
        s['turn_index'] += 1
        if not scene_judgment.enabled(package['story']) and len(s['active']['turns']) + 1 >= node.get('max_turns', 8):
            result['ends'] = True
            result['outcome'] += ' 这次会面告一段落，未解决的疑问留待后续。'
        return result

    def finish_turn(self, s, request, reply, result, usage):
        s['active']['turns'].append({'input': request.message, 'reply': reply,
                                   'channel':request.channel,'listeners':result.get('listeners',[])})
        s['usage'].append(usage)
        if result['ends']:
            self.close_event(s, resolved_exit=True)
        self.store.save_session(s)
        self.session_files(s).save_notes('旅程', s['id'], notebook(s))

    def close_event(self, s, resolved_exit=False):
        if scene_judgment.enabled(self.package(s['revision'])['story']) and not resolved_exit:
            raise ValueError('请用本幕的离开或结算行动结束，避免跳过必要步骤')
        if not s['active'] or not s['active']['turns']:
            raise ValueError('至少完成一次交互才能结束事件')
        active = s['active']
        s['completed'].append(active['node'])
        exit_flag = self.node(s).get('exit_flag')
        if exit_flag:
            s['flags'][exit_flag] = True
        # Settle the event from the committed state diff; the replies stay intact in `turns`.
        summary = event_summary(s, active, self.package(s['revision']))
        archive = {**active, 'summary': summary, 'after': self.snapshot(s)}
        s['archives'].append(archive)
        s['active'] = None
        story = self.package(s['revision'])['story']
        ending = None if s.get('ending') else endings_rules.resolve(s, story)
        if ending is not None:
            # A phase ending is sticky: it is recorded once and never re-derived from
            # later prose or later pressure effects. Everything afterwards still moves
            # flags and resources (a "lost" ending keeps going), but the recorded ending
            # is never overwritten by a later condition that happens to match — otherwise
            # pressure and endings could overwrite each other.
            s['ending'] = {**ending, 'at': s['time']}
            follow = ending.get('continue_event')
            if follow and follow in {e['id'] for e in story['events']} \
                    and follow not in s['completed']:
                # A dedicated session key, not a field inside the start receipt: an
                # ending without a start profile must not fabricate one.
                s['forced_entry'] = follow
        # Continue sub-events inside the same major scene without creating a chat.
        if any(e.get('major_scene_id', e['location_id']) == s.get('last_scene_id', s.get('conversation', {}).get('scene_id')) for e in self.candidates(s)):
            self.enter(s)

    def rollback(self, s, archive_id):
        index = next((i for i, a in enumerate(s['archives']) if a['id'] == archive_id), None)
        if index is None:
            raise ValueError('事件存档不存在')
        archive = s['archives'][index]
        restored = copy.deepcopy(archive['before'])
        # Persistence version is metadata, not game state; retain the version read
        # from the current save so rollback itself remains an atomic compare-and-swap.
        restored['state_version'] = s.get('state_version', 0)
        restored['archives'] = copy.deepcopy(s['archives'][:index])
        restored['active'] = None
        self.enter(restored)
        self.store.save_session(restored)
        self.session_files(restored).save_notes('旅程', restored['id'], notebook(restored))
        return restored

    def resolve_action(self, s, node, request, story):
        """解析这次要执行的动作：(action, plan, duration)。全部校验在副作用之前。

        命名空间：静态 ``node['actions']`` 优先（旧按钮行为不变）；找不到时再在当前算出的
        运行时方案里找（id 以 ``adventure:`` 开头）。

        动态方案**必须**带确认凭据：方案是运行时算出来的，玩家看到的成本/时长/目标是
        一份快照，不校验就等于允许拿旧摘要执行当下的不同动作。静态动作不传凭据时仍是
        旧的直接按钮行为（有意的兼容，不是语义放宽）。

        ``plan`` 与凭据验证用的是**同一次**计算结果，所以不存在「凭据验了 node.actions
        而执行时找不到动态动作」的缺口。
        """
        package = self.package(s['revision'])
        plans, refused = adventure_actions.scan(
            s, package['story'], package['characters'])
        plan = next((p for p in plans if p['action_id'] == request.action_id), None)
        action = next((a for a in node.get('actions') or []
                       if a['id'] == request.action_id), None)
        if action is None and plan is not None and plan.get('supported'):
            action = plan['action']
        if action is None or action['id'] in ((s.get('active') or {}).get('actions_done') or []):
            raise ValueError('操作不存在或已经执行')
        confirm = getattr(request, 'confirm', None)
        if action.get('requires_confirmation') and not confirm:
            raise ValueError('这个行动有明确风险，请先查看并确认后果')
        if plan is not None and plan.get('action') is action and not confirm:
            raise ValueError('这个行动需要先确认（成本、时长与目标以确认摘要为准）')
        if confirm:
            free_actions.verify(s, package['story'], node, action['id'], confirm,
                                plans=plans, characters=package['characters'])
        if not all(s['flags'].get(k, False) == v
                   for k, v in (action.get('requires') or {}).items()):
            raise ValueError('操作条件尚未满足')
        if not local_rules.affordable(s, package['story'], action):
            raise ValueError('资源不足，无法执行该行动')
        duration = action.get('duration_hours', local_rules.rules(package['story']).turn_hours)
        return action, plan, duration

    def local_action(self, s, action_id, confirm=None):
        """在没有进行中的事件时执行一个**运行时方案**（休息等本地动作）。

        返回语义固定如下，调用方不需要猜：

        * 只在候选副本上执行，**不写库、不改入参 ``s``**；成功时返回 ``(result, work)``。
        * 调用方（``Service``）在一次短锁内把 ``work`` 写回并 ``save_session`` 一次，
          因此不会出现双重保存 / 双版 ``state_version``。
        * 没有 ``active`` 事件时不记录对话轮，只写已结算的本地记录：
          ``local.ledger``（资源）、``checks``（检定）、``facts``/``heard``（声明效果），
          以及一行很小的 ``local_actions`` 审计条目。
        * 确认凭据与活动内动作用同一个 ``free_actions.confirm_token``（``node`` 为空串）。
        * 任何不满足（不存在/条件不足/资源不足/凭据过期/旁观模式）都在写入前抛错。
        """
        if s.get('active'):
            raise ValueError('当前有进行中的事件，请用既有动作管线')
        package = self.package(s['revision'])
        story, characters = package['story'], package['characters']
        if adventure_actions.config(story) is None:
            raise ValueError('故事包没有声明通用行动')
        plans, refused = adventure_actions.scan(s, story, characters)
        plan = next((p for p in plans if p['action_id'] == action_id), None)
        if plan is not None and plan['kind'] == 'travel':
            # 旅行有它自己的入口（地图移动），不在这里结算。
            raise ValueError('旅行请用地图移动（同一个时钟，不另外结算）')
        if plan is None or not plan['supported'] or plan.get('action') is None:
            hit = next((r for r in refused if r['action_id'] == action_id), None)
            raise ValueError(hit['text'] if hit else '这里没有可确认的这个行动')
        if s['mode'] == 'observer':
            raise ValueError('旁观阶段不能直接操作人物和物品')
        if not confirm:
            raise ValueError('这个行动需要先确认（成本、时长与效果以确认摘要为准）')
        free_actions.verify(s, story, None, action_id, confirm,
                            plans=plans, characters=characters)
        action = plan['action']
        work = copy.deepcopy(s)
        before = {'time': s['time'],
                  'resources': dict((s.get('local') or {}).get('resources') or {})}
        local_rules.charge(work, story, action, 'local:' + action_id)
        audits = self.effects(work, action.get('effects', []), 'local:' + action_id)
        pressure_rules.advance(work, story, characters, plan['duration_hours'],
                               effects=self.effects)
        work['local_actions'] = list(work.get('local_actions') or []) + [{
            'action': action_id, 'kind': plan['kind'],
            'at': work['time'], 'hours': plan['duration_hours']}]
        result = {'outcome': action.get('success_text') or action['label'],
                  'kind': plan['kind'], 'duration_hours': plan['duration_hours'],
                  'ends': False, 'listeners': [],
                  # 本次服务端已确认的结果：时长与资源确实变化了多少。只含公开字段，
                  # 不推测隐藏恢复、不把并发更新冒称本次效果。
                  'local_result': {
                      'action_id': action_id, 'kind': plan['kind'],
                      'hours': work['time'] - before['time'],
                      'label': action['label'],
                      'resources': [{'id': rid, 'before': before['resources'].get(rid, 0),
                                     'after': (work.get('local') or {})
                                              .get('resources', {}).get(rid, 0)}
                                    for rid in sorted(action.get('costs') or {})]}}
        public = rewards_rules.public_result(rewards_rules.rules(story), audits, work)
        if public:
            result['rewards'] = public
        return result, work

    def adventure_plans(self, s):
        """当前可用的运行时方案（纯函数：不写 session、不写库）。

        包没有声明 ``mechanics.adventure`` 时返回空列表，因此老包的 surface 与确认
        路径完全不变。
        """
        package = self.package(s['revision'])
        return adventure_actions.build(s, package['story'], package['characters'])

    def require_travel(self, s, destination):
        """确认这个目的地当前是一个**合法旅行方案**，否则在副作用前拒绝。

        这里不做新的判定：判定只有一个地方（``adventure_actions``），本方法只是把结果
        转成异常。所以「已知但被条件封锁的路线」不能靠直接调 ``move`` 绕过去，
        ``world_mismatch`` / ``route_cost`` 之类缺口同样走不进去。
        """
        package = self.package(s['revision'])
        plans, refused = adventure_actions.scan(s, package['story'], package['characters'])
        wanted = 'adventure:travel:' + str(destination)
        if any(p['action_id'] == wanted and p['supported'] and p.get('travel')
               for p in plans):
            return
        hit = next((r for r in refused if r['action_id'] == wanted), None)
        if hit is not None:
            raise ValueError(hit['text'])
        raise ValueError('这里没有通向该地点的路线')

    def travel_hours(self, s, destination):
        """这次移动**真实**会推进的小时数与来源。

        有 ``mechanics.adventure`` 时，作者声明的路线耗时（``route.hours`` 或 travel 模板的
        ``duration_hours``）优先，否则落回既有的 ``mechanics.local.travel_hours``；没有该
        声明块的旧包永远返回 ``local.travel_hours`` —— 旧行为一个字不变。

        这里只决定时长，不决定能不能走：相邻性、可见性与条件仍由 :meth:`move` 与
        运行时方案的复核负责。
        """
        package = self.package(s['revision'])
        story = package['story']
        default_hours = local_rules.rules(story).travel_hours
        if adventure_actions.config(story) is None:
            return default_hours, 'local.travel_hours'
        plan = free_actions.dynamic_plan(
            s, story, 'adventure:travel:' + str(destination),
            characters=package['characters'])
        if plan is not None and plan.get('supported') and plan.get('travel'):
            return plan['duration_hours'], plan['duration_source']
        return default_hours, 'local.travel_hours'

    def move(self, s, destination, hours=None):
        """移动一个相邻地点，并**只**用 ``pressure_rules.advance`` 推进时钟。

        ``hours`` 只给内部可信调用方（例如按已确认的旅行方案推进）：它不来自请求参数。
        缺省时取 :meth:`travel_hours`，所以作者声明的路线耗时会真正生效，不会出现
        「界面承诺 3 小时、实际推进 2 小时」。
        """
        if s['active']:
            raise ValueError('先结束当前事件，再前往下一地点')
        package = self.package(s['revision'])
        story, characters = package['story'], package['characters']
        places = story['locations']
        current = next(l for l in places if l['id'] == s['location'])
        if destination not in current['neighbors']:
            raise ValueError('只能前往相邻地点')
        # 新机制包：能走的路必须先是**当前算得出的合法旅行方案**，否则已知但被条件封锁的
        # 路线只要直接 POST /move 就绕过了方案层。旧包（无声明块）保持原有规则。
        plan = None
        if adventure_actions.config(story) is not None:
            self.require_travel(s, destination)
            plan = free_actions.dynamic_plan(
                s, story, 'adventure:travel:' + str(destination), characters=characters)
        if hours is None:
            hours = self.travel_hours(s, destination)[0]
        costs = dict((plan or {}).get('travel', {}).get('costs') or {})
        # 整次移动在**候选副本**上完成：先扣费、再改位置/推进时钟/进入事件，任何一步失败
        # 都不回写调用方的 session（不会出现“钱扣了但压力阶段失败”的半提交）。
        work = copy.deepcopy(s)
        if costs:
            local_rules.charge(work, story, {'costs': costs}, 'move:' + str(destination))
        work['location'] = destination
        pressure_rules.advance(work, story, characters, hours, effects=self.effects)
        if work['mode'] == 'protagonist':
            work['characters'][work['hero']]['location'] = destination
        if destination not in work['explored']:
            work['explored'].append(destination)
        self.enter(work)
        s.clear()
        s.update(work)
        # 一次保存；CAS 仍是已有的 state_version。持久化失败时调用方拿到异常，
        # 且 state_version 未递增，不会伪装成已执行。
        self.store.save_session(s)

    def adventure_surface(self, s, package, node):
        """玩家可见的运行时方案段；包没声明 ``mechanics.adventure`` 时返回 ``None``。

        三条约束：

        1. 只用 ``adventure_actions.public()`` 的白名单字段——线索正文、分支正文、未发生
           的结果都不进来；
        2. 只有方案真的带可执行 action 且 ``supported`` 才附 ``confirm``；缺口（转交/实例/
           带路费/带效果的休息）不附，避免“看着能点、一点就废”的按钮。
        3. 事件未结束时旅行不装成可执行：标 ``blocked_active_event`` 并给一句公开可操作提示。
        """
        story = package['story']
        if adventure_actions.config(story) is None:
            return None
        plans, refused = adventure_actions.scan(s, story, package['characters'])
        rows = []
        for plan in plans:
            view = adventure_actions.public(plan, story)
            if plan['action'] is not None and plan['supported']:
                view['confirm'] = free_actions.confirm_token(s, node, plan['action'], story)
            if plan['kind'] == 'travel' and s['active']:
                view['execution'] = 'blocked_active_event'
                view['hint'] = '先结束当前事件，再前往相邻地点'
            elif plan['kind'] == 'travel':
                view['execution'] = 'move'
            elif plan['kind'] == 'rest' and plan['supported']:
                view['execution'] = 'wait'
            else:
                view['execution'] = 'action' if view.get('confirm') else 'unsupported'
            rows.append(view)
        return {'plans': rows,
                'refused': [{'action_id': r['action_id'], 'kind': r['kind'],
                             'target': r['target'], 'reason': r['reason'],
                             'text': r['text']} for r in refused],
                'note': '这些目标是作者已配置且当前可见的；确认摘要不含未发生的结果。'
                        '记账仍由既有动作管线/等待/移动完成，本段只是一个读视图。'}

    def surface(self, s):
        p = self.package(s['revision'])
        places = p['story']['locations']
        current = next(l for l in places if l['id'] == s['location'])
        visible = set(s['explored']) | set(current['neighbors'])
        node = self.node(s) if s['active'] else None
        # Each action carries its cost and duration so the UI can show what confirming
        # actually commits to; the confirm token is only handed out by /confirm/{action}.
        # A package that declares none of the demo mechanics keeps the legacy two-field
        # action shape, so an old package's surface payload stays byte-identical.
        detailed = any(key in (p['story'].get('mechanics') or {})
                       for key in ('start_profiles', 'pressure', 'endings', 'traits'))
        available = [] if not node else [
            a for a in node['actions']
            if a['id'] not in s['active']['actions_done']
            and all(s['flags'].get(k, False) == v for k, v in a.get('requires', {}).items())
            and local_rules.affordable(s, p['story'], a)]
        if detailed:
            actions = []
            for a in available:
                summary = free_actions.summarise(a, p['story'])
                actions.append({'id': a['id'], 'label': a['label'],
                                'costs': summary['costs'],
                                'duration_hours': summary['duration_hours'],
                                'check': summary['check'],
                                'ends_event': summary['ends_event']})
        else:
            actions = [{'id': a['id'], 'label': a['label']} for a in available]
        if s['mode'] == 'observer' or (s['mode'] == 'mixed' and node and not node.get('player_enters', False)):
            actions = []
        adventure = self.adventure_surface(s, p, node)
        fatigue = s['characters'][s['hero']]['status'].get('疲劳', 0)
        surface = {'id': s['id'], 'title': s['title'], 'world': p['story']['title'], 'mode': s['mode'],
                'abilities':{'values':attributes.values(next(c for c in p['characters']['characters'] if c['id']==s['hero']).get('attributes'),legacy=True),
                    'health':attributes.health(next(c for c in p['characters']['characters'] if c['id']==s['hero']),s['characters'][s['hero']]['status'])},
                'local_state':local_rules.view(s,p['story']),
                'geography':local_environment(p['story'],s),
                'atlas':project_atlas(p['story'],s),
                'current_scene': next((x['title'] for x in p['story'].get('major_scenes', []) if x['id'] == s.get('last_scene_id')), current['name']),
                'conversations': self.conversations(s),
                'conversation_id': (s.get('conversation') or {}).get('id'), 'revision': s['revision'],
                'location': current['name'], 'status': '心力交瘁' if fatigue > 0.75 else '略感疲惫' if fatigue > 0.4 else '精神尚可',
                'daytime': '白昼' if is_daylight(p['story'],s) else '夜间',
                'event': {'title': node['title'], 'goal': node['player_goal']} if node else None,
                'turns': s['active']['turns'] if s['active'] else [], 'actions': actions,
                'archives': [{'id': a['id'], 'title': a['title'], 'turns': a['turns']} for a in s['archives']],
                'places': [{'id': l['id'], 'name': l['name'], 'coordinates': l.get('coordinates', [0, 0]), 'explored': l['id'] in s['explored'], 'current': l['id'] == s['location'], 'can_move': l['id'] in current['neighbors'] and not s['active']} for l in places if l['id'] in visible],
                'inventory': [i['name'] for i in p['story']['items'] if i['id'] in s['inventory']],
                'elements': self.project_elements(s, 'player')}
        if rewards_rules.rules(p['story']):
            # The legacy `inventory` string list stays exactly as it was; the structured
            # holding view is added only when the author configured rewards.
            surface['rewards'] = rewards_rules.public_state(s, p['story'], 'player')
        if scene_judgment.enabled(p['story']):
            surface['short_scene'] = {'description': current.get('description', ''),
                                      'travel_hours': local_rules.rules(p['story']).travel_hours}
        exploration = civ_exploration.surface(s, p['story'], adventure)
        if exploration is not None:
            surface['exploration'] = exploration
        # Only towns bound to a place in THIS revision *and* within what this journey
        # knows reach the player view, and only through the public whitelist.
        town = towns_store.story_towns(p['story'], s['revision'], s)
        if town:
            surface['towns'] = town
        # Start receipt, known warnings and the current phase ending. Each is omitted
        # entirely when the package declares nothing, so an untouched package produces
        # exactly the previous surface payload.
        opening = start_rules.surface(s, p['story'])
        if opening is not None:
            surface['opening'] = opening
        warnings = pressure_rules.known(s, p['story'], 'player')
        if warnings:
            surface['warnings'] = [row['text'] for row in warnings]
        ending = s.get('ending') or endings_rules.resolve(s, p['story'])
        if ending is not None:
            surface['ending'] = ending
        if adventure is not None:
            surface['adventure'] = adventure
        # 世界历史（玩家视角）。键名区别于 ``conversations``/``history`` 消费方。
        chronicle = self.world_history(s, p['story'], 'player')
        if chronicle is not None:
            surface['world_history'] = chronicle
        return surface

    def approve(self, draft):
        if draft['status'] != 'draft':
            raise ValueError('该候选已经处理')
        if draft['base_revision'] != self.package()['id']:
            raise ValueError('故事包已有更新，请重新生成或编辑后重新提交')
        e = Element.model_validate(draft['element']).model_dump()
        p = copy.deepcopy(self.package())
        data = e['data']
        if e['kind'] == 'worldview':
            p['story']['worldview'] = data
        elif e['kind'] != 'fact':
            group = p['characters']['characters'] if e['kind'] == 'character' else p['story'][{'item': 'items', 'place': 'locations', 'event': 'events'}[e['kind']]]
            if 'id' not in data:
                raise ValueError('元素需要 ID')
            old = next((i for i, item in enumerate(group) if item['id'] == data['id']), None)
            if old is None:
                group.append(data)
            else:
                group[old] = data
        for key in e['public_fields']:
            if key not in data or not isinstance(data[key], (str, int, float, bool)):
                raise ValueError('公开字段必须存在且为单个文本或数值，不能公开整个嵌套对象')
        if e['location_id'] and e['location_id'] not in {l['id'] for l in p['story']['locations']}:
            raise ValueError('可见性地点不存在')
        if set(e['known_by']) - ({'player'} | {c['id'] for c in p['characters']['characters']}):
            raise ValueError('可见性受众不存在')
        elements = p['story'].setdefault('elements', [])
        elements[:] = [v for v in elements if not (v['kind'] == e['kind'] and v['data'].get('id') == data.get('id'))]
        elements.append(e)
        revision = self.commit_package(p['story'], p['characters'], draft['instruction'], approved_draft=draft)
        return revision
