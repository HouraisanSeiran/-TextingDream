# -*- coding: utf-8 -*-
"""运行期行动的真实玩家入口：Playwright 浏览器测试（隔离临时库）。

它验证的是**前端真的消费了** `surface.adventure`，而不是「接口返回了就算」：

* 观察/调查：点按钮 → 同一个确认框 → POST /chat → 状态真的变、成本真的扣；
* 旅行：点按钮 → 确认目的地/时长/路费 → POST /move → 位置、时钟、路费一次提交；
* 无事件休息：POST /chat 早返回没有模型正文，但必须有**服务端已确认**的回执；
* 缺执行器的方案（物品实例/转交）**不出现按钮**；
* 旧静态动作仍然能点；
* 1440 不溢出；1366 只作布局代表图。

夹具自包含：临时根 + 一个声明 `mechanics.adventure` 与 `mechanics.map` 的故事包，
外加一个**没有任何事件**的地点，用来测无事件休息。
"""
import copy
import json
import shutil
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def adventure_block():
    return {
        'version': 1,
        'clues': [
            {'id': 'clue_waterline', 'target': {'kind': 'place', 'id': 'plaza'},
             'action_kinds': ['observe'],
             'effects': [{'op': 'information', 'text': '石阶上的水痕还是湿的。',
                          'known_by': ['player'], 'confirmed': True}]},
            {'id': 'clue_ledger', 'target': {'kind': 'object', 'id': 'ledger'},
             'action_kinds': ['investigate'],
             'effects': [{'op': 'information', 'text': '这一页的米价被人改过。',
                          'known_by': ['player']}]},
        ],
        'topics': [
            {'id': 'ask_price', 'kind': 'ask', 'target': {'kind': 'npc', 'id': 'merchant'},
             'answers': [{'when': {}, 'success_text': '他把米价说了一遍。',
                          'effects': [{'op': 'information', 'text': '米价三日内涨了两成。',
                                       'known_by': ['player']}]}]},
        ],
        'routes': [
            {'origin': 'plaza', 'destination': 'gate', 'kind': 'causeway', 'hours': 3,
             'import_id': 'mi_abc123'},
        ],
        'templates': [
            {'kind': 'rest', 'label': '原地歇 {hours} 小时',
             'costs': {'food': 1}, 'intent_aliases': ['歇一会']},
            {'kind': 'travel', 'target': {'kind': 'place', 'id': 'gate'},
             'label': '过闸去{target}', 'costs': {'coin': 1}, 'intent_aliases': ['过闸']},
            # 转交没有执行器：必须**不出现**按钮。
            {'kind': 'give', 'target': {'kind': 'object', 'id': 'ledger'},
             'recipients': ['merchant'], 'label': '把{target}交给{npc}'},
        ],
        'rest_hours': 4, 'max_rest_hours': 168,
    }


def story_doc():
    return {
        'id': 'ui-test', 'title': '界面接入测试', 'premise': '界面测试用的小世界。',
        'character_package_id': 'ui-test-characters',
        'locations': [
            {'id': 'plaza', 'name': '米市街', 'description': '街面有水痕。',
             'neighbors': ['gate', 'empty_place'], 'scenes': []},
            {'id': 'gate', 'name': '上闸', 'description': '', 'neighbors': ['plaza'],
             'scenes': [], 'coordinates': [120.5, 30.25]},
            # 没有任何事件的地点：在那里只能休息/移动。
            {'id': 'empty_place', 'name': '仓前空地', 'description': '',
             'neighbors': ['plaza'], 'scenes': []},
        ],
        'events': [
            {'id': 'root_event', 'title': '米市街的清晨', 'location_id': 'plaza',
             'participants': ['player', 'merchant'], 'player_goal': '弄清米价',
             'player_enters': True, 'next_events': [], 'entry_flags': {},
             'exit_flag': 'done_root', 'max_turns': 30,
             'actions': [{'id': 'look', 'label': '看看街面', 'ends_event': False,
                          'success_text': '我先看了看街面。'},
                         {'id': 'done_talk', 'label': '谈完了', 'ends_event': True,
                          'success_text': '这次谈话告一段落。'}]},
        ],
        'items': [
            {'id': 'ledger', 'name': '账页', 'description': '', 'authority': 'engine',
             'location_id': 'plaza'},
        ],
        'mechanics': {
            'local': {'resources': [{'id': 'coin', 'name': '铜币', 'unit': '枚',
                                     'initial': 10, 'maximum': 50},
                                    {'id': 'food', 'name': '口粮', 'unit': '份',
                                     'initial': 3, 'maximum': 9}],
                      'turn_hours': 1, 'travel_hours': 2},
            'map': {'kind': 'civ_atlas', 'import_id': 'mi_abc123'},
            'adventure': adventure_block(),
        },
    }


def characters_doc():
    axes = {'talent': 50, 'strength': 45, 'agility': 55, 'wisdom': 60,
            'social': 65, 'resilience': 50}
    return {'id': 'ui-test-characters', 'title': '界面测试角色', 'characters': [
        {'id': 'player', 'name': '我', 'role': '主角', 'location_id': 'plaza',
         'personality': {'谨慎': 0.6}, 'state': {'疲劳': 0.1}, 'attributes': dict(axes)},
        {'id': 'merchant', 'name': '米商', 'role': '次要角色', 'location_id': 'plaza',
         'personality': {'社交': 0.6}, 'state': {}, 'attributes': dict(axes)},
    ]}


def write_package(root):
    folder = root / 'StoryPackage' / '玄陆'
    folder.mkdir(parents=True)
    (folder / 'story.json').write_text(
        json.dumps(story_doc(), ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / '总概.md').write_text('# 界面接入测试\n\n夹具世界。\n', encoding='utf-8')
    (folder / '知识点').mkdir()
    chars = root / 'character_packages'
    chars.mkdir()
    body = json.dumps(characters_doc(), ensure_ascii=False, indent=2)
    (chars / 'ui-test-characters.json').write_text(body, encoding='utf-8')
    # 空库首次初始化会固定读这个文件名（既有约定）。
    (chars / 'xuanlu_初始角色包.json').write_text(body, encoding='utf-8')
    return folder


class BrowserCase(unittest.TestCase):
    """起一个绑定临时库的真实 uvicorn，用 msedge 跑一遍。"""

    viewport = {'width': 1440, 'height': 1000}

    def setUp(self):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:                                     # pragma: no cover
            self.skipTest('playwright 未安装')
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write_package(self.root)
        self.server = None

    def tearDown(self):
        if self.server is not None:
            self.server.should_exit = True
        self.tmp.cleanup()

    def start(self):
        import uvicorn
        from app import web
        from unittest.mock import patch
        # 静态资源：把真实的 app/static 与 assets 复制到临时根下，页面才拿得到脚本。
        # （不软链接：Windows 上普通用户无 symlink 权限。）
        shutil.copytree(ROOT / 'app' / 'static', self.root / 'app' / 'static',
                        dirs_exist_ok=True)
        (self.root / 'assets' / 'maps').mkdir(parents=True, exist_ok=True)
        self.patched = patch.object(web, 'ROOT', self.root)
        self.patched.start()
        app = web.create_app(self.root / 'ui.sqlite3')
        app.state.service.provider.configure({'offline': True})
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(128)
        self.url = 'http://127.0.0.1:%s' % listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
        worker = threading.Thread(target=lambda: server.run(sockets=[listener]),
                                  daemon=True)
        worker.start()
        for _ in range(120):
            if server.started:
                break
            time.sleep(0.1)
        self.server, self.app = server, app
        return app

    # ------------------------------------------------------------------ 帮手
    def session(self, sid):
        return self.app.state.service.store.session(sid)

    def surface_actions(self):
        return self.app.state.service.runtime.surface(
            self.app.state.service.store.all('session')[-1])

    def run_flow(self, page):
        """主流程：建旅程 → 观察 → 旅行 → 无事件休息。"""
        from playwright.sync_api import expect
        page.goto(self.url)
        page.locator('#session-title').fill('界面接入')
        page.locator('#new-form .primary').click()
        page.locator('#actions button').first.wait_for()
        sid = self.app.state.service.store.all('session')[-1]['id']
        before = self.session(sid)

        # 1) 观察：动态按钮出现，点开走同一个确认框。
        observe = page.locator('#actions button[data-adventure-id="adventure:observe:plaza"]')
        expect(observe).to_be_visible()
        observe.click()
        expect(page.locator('#demo-confirm')).to_be_visible()
        expect(page.locator('#demo-confirm-body')).to_contain_text('观察米市街')
        page.locator('#demo-confirm-run').click()
        expect(page.locator('#actions button[data-adventure-id="adventure:observe:plaza"]')
               ).to_have_count(0, timeout=15000)
        after = self.session(sid)
        self.assertIn('石阶上的水痕还是湿的。', [r['text'] for r in after['facts']])
        self.assertEqual(after['time'], before['time'] + 1)

        # 2) 缺执行器的转交：从不出现按钮。
        self.assertEqual(
            page.locator('#actions button[data-adventure-id^="adventure:give:"]').count(), 0)

        # 3) 旧静态动作仍可点。
        look = page.locator('#actions button[data-action-id="look"]')
        expect(look).to_be_visible()

        # 4) 结束事件 → 旅行可用（事件未结束时它是 blocked，不给按钮）。
        done = page.locator('#actions button[data-action-id="done_talk"]')
        done.click()
        page.locator('#demo-confirm-run').click()
        expect(page.locator('#actions button[data-adventure-id="adventure:travel:gate"]')
               ).to_be_visible(timeout=15000)
        time_before = self.session(sid)['time']
        coin_before = self.session(sid)['local']['resources']['coin']
        page.locator('#actions button[data-adventure-id="adventure:travel:gate"]').click()
        expect(page.locator('#demo-confirm-body')).to_contain_text('前往 上闸')
        expect(page.locator('#demo-confirm-body')).to_contain_text('3 小时')
        expect(page.locator('#demo-confirm-body')).to_contain_text('路费')
        page.locator('#demo-confirm-run').click()
        expect(page.locator('#location')).to_contain_text('上闸', timeout=15000)
        moved = self.session(sid)
        self.assertEqual(moved['location'], 'gate')
        self.assertEqual(moved['time'], time_before + 3)         # 声明的 3 小时
        self.assertEqual(moved['local']['resources']['coin'], coin_before - 1)

    def test_1440_main_flow(self):
        from playwright.sync_api import sync_playwright
        self.start()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport=self.viewport)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            try:
                self.run_flow(page)
                overflow = page.evaluate(
                    'document.documentElement.scrollWidth > window.innerWidth + 1')
                self.assertFalse(overflow, '1440 出现横向溢出')
                self.assertEqual(errors, [], '页面出现 JS 错误：%s' % errors)
                page.screenshot(path=str(self.root / 'ui-1440.png'), full_page=True)
            finally:
                browser.close()


class RestWithoutEventTests(BrowserCase):
    """无事件休息：必须有服务端已确认的回执，且版本只增 1。"""

    viewport = {'width': 1440, 'height': 1000}

    def test_rest_after_event_shows_confirmed_receipt(self):
        from playwright.sync_api import expect, sync_playwright
        app = self.start()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport=self.viewport)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            try:
                page.goto(self.url)
                page.locator('#session-title').fill('无事件休息')
                page.locator('#new-form .primary').click()
                page.locator('#actions button').first.wait_for()
                sid = app.state.service.store.all('session')[-1]['id']
                # 结束事件 → 该地点没有别的事件可进 → active 为 None。
                page.locator('#actions button[data-action-id="done_talk"]').click()
                page.locator('#demo-confirm-run').click()
                expect(page.locator('#actions button[data-adventure-id^="adventure:rest:"]')
                       ).to_be_visible(timeout=15000)
                session = self.session(sid)
                self.assertIsNone(session['active'])
                version_before = session['state_version']
                food_before = session['local']['resources']['food']
                time_before = session['time']

                page.locator('#actions button[data-adventure-id^="adventure:rest:"]').click()
                expect(page.locator('#demo-confirm-body')).to_contain_text('成本：口粮')
                page.locator('#demo-confirm-run').click()
                # 关键：没有模型正文，但必须有服务端已确认的回执。
                expect(page.locator('#notice')).to_contain_text('已执行', timeout=15000)
                expect(page.locator('#notice')).to_contain_text('口粮')
                after = self.session(sid)
                self.assertEqual(after['time'], time_before + 4)
                self.assertEqual(after['local']['resources']['food'], food_before - 1)
                self.assertEqual(after['state_version'], version_before + 1)
                # 回执不写进对话历史（不冒充模型回复）。
                self.assertEqual((after.get('active') or {}).get('turns', []), [])
                self.assertEqual([a['turns'] for a in after['archives']], [1])
                self.assertEqual(errors, [])
            finally:
                browser.close()


class NarrowLayoutTests(BrowserCase):
    """1366 只做布局代表图（不重复功能流）。"""

    viewport = {'width': 1366, 'height': 900}

    def test_1366_no_horizontal_overflow(self):
        from playwright.sync_api import sync_playwright
        self.start()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport=self.viewport)
            try:
                page.goto(self.url)
                page.locator('#session-title').fill('1366 布局')
                page.locator('#new-form .primary').click()
                page.locator('#actions button').first.wait_for()
                overflow = page.evaluate(
                    'document.documentElement.scrollWidth > window.innerWidth + 1')
                self.assertFalse(overflow, '1366 出现横向溢出')
                page.screenshot(path=str(self.root / 'ui-1366.png'), full_page=True)
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()
