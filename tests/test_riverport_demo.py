# -*- coding: utf-8 -*-
"""河港汛期：包体自包含 + 三起点离线 E2E + 投影不泄漏。

全部离线（provider offline，不发任何网络请求），城镇与特质只用包内快照。
"""
import asyncio
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app import pressure as P
from app.contracts import Turn
from app.service import Service
from app.storage import Store

REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / 'StoryPackage' / '河港汛期'
CHARACTERS = REPO / 'character_packages' / 'riverport-demo-characters-001.json'


def make_service(root=None):
    tmp = tempfile.TemporaryDirectory() if root is None else None
    root = Path(root or tmp.name)
    library = root / 'StoryPackage'
    library.mkdir(parents=True)
    shutil.copytree(PACKAGE, library / '河港汛期')
    chars = root / 'character_packages'
    chars.mkdir()
    shutil.copy(CHARACTERS, chars / CHARACTERS.name)
    svc = Service(Store(root / 'riverport.sqlite3'), REPO)
    svc.provider.configure({'offline': True})
    svc.runtime.activate_package('河港汛期')
    return tmp, svc


def reload(svc, session):
    return svc.store.session(session['id'])


def turn(svc, session, action=None, message='继续', channel='action'):
    asyncio.run(svc.turn(session['id'], Turn(message=message, action_id=action,
                                            channel=channel)))
    return reload(svc, session)


def wait_hours(svc, session, hours):
    """和 /api/sessions/{id}/wait 同一条路径：一个时钟，先推进再进入事件。"""
    s = reload(svc, session)
    story = svc.runtime.package(s['revision'])
    P.advance(s, story['story'], story['characters'], hours,
              effects=svc.runtime.effects)
    svc.runtime.enter(s)
    svc.store.save_session(s)
    return reload(svc, session)


def move(svc, session, destination):
    s = reload(svc, session)
    svc.runtime.move(s, destination)
    return reload(svc, session)


def free_exit(node):
    """当前事件里那个「无前置、无花费」的结束出口。每个节点都必须有。"""
    for action in node.get('actions') or []:
        if action.get('ends_event') and not action.get('costs') \
                and not action.get('requires'):
            return action['id']
    raise AssertionError('节点缺少无前置无花费的结束出口：%s' % node['id'])


def settle(svc, session, steps=4):
    """用免费出口把自动进入的旁支事件逐个走完，直到可以移动。"""
    s = reload(svc, session)
    for _ in range(steps):
        if not s['active']:
            break
        s = turn(svc, s, free_exit(svc.runtime.node(s)))
    return s


class RiverportPackageTests(unittest.TestCase):
    def test_activation_does_not_touch_other_packages(self):
        tmp, svc = make_service()
        try:
            folders = [row['folder'] for row in svc.runtime.list_packages()]
            self.assertIn('河港汛期', folders)
            self.assertIn('玄陆', folders)
            self.assertNotEqual(svc.runtime.files.directory.name, '玄陆')
            # 灰烬海目录原本就在，未被改写
            self.assertTrue((REPO / 'StoryPackage' / '灰烬海' / 'story.json').exists())
        finally:
            if tmp:
                tmp.cleanup()

    def test_three_starts_differ_in_identity_place_items_money_known_and_entry(self):
        tmp, svc = make_service()
        try:
            rows = {}
            for profile in ('riverport_local', 'outside_traveller', 'guild_apprentice'):
                s = svc.runtime.new_session('河港-' + profile, 'protagonist',
                                            profile_id=profile)
                rows[profile] = {'location': s['location'],
                                 'node': s['active']['node'],
                                 'wallet': dict(s['rewards']['wallet']),
                                 'inventory': list(s['inventory']),
                                 'known': [row['text'] for row in s['heard']],
                                 'goal': s['start']['goal']}
            places = {row['location'] for row in rows.values()}
            self.assertEqual(len(places), 3)
            self.assertEqual(len({row['node'] for row in rows.values()}), 3)
            self.assertEqual(len({json.dumps(row['wallet'], sort_keys=True)
                                  for row in rows.values()}), 3)
            # 入口事件不被同地点的第一个根节点抢占：本地居民落的是 grain_price，
            # 而不是事件表里排在它前面的 stall_repair。
            self.assertEqual(rows['riverport_local']['node'], 'grain_price')
            self.assertTrue(rows['riverport_local']['inventory'])
            self.assertNotEqual(rows['riverport_local']['known'],
                                rows['outside_traveller']['known'])
        finally:
            if tmp:
                tmp.cleanup()

    def test_package_is_self_contained_in_an_empty_library(self):
        tmp, svc = make_service()
        other = tempfile.TemporaryDirectory()
        try:
            package = copy.deepcopy(svc.runtime.package())
            empty_svc = Service(Store(Path(other.name) / 'empty.sqlite3'), REPO)
            empty_svc.provider.configure({'offline': True})
            empty_svc.runtime.commit_package(package['story'], package['characters'],
                                             '导出导入')
            session = empty_svc.runtime.new_session('导入后旅程', 'protagonist',
                                                   profile_id='riverport_local')
            surface = empty_svc.runtime.surface(session)
            self.assertTrue(surface['towns'])
            self.assertEqual(surface['opening']['profile_id'], 'riverport_local')
            traits = empty_svc.runtime.context(session, 'player', '看看掌柜',
                                               empty_svc.preferences())
            self.assertIn('current_traits', traits)
        finally:
            other.cleanup()
            if tmp:
                tmp.cleanup()

    def test_hidden_traits_and_internal_state_never_reach_the_player_view(self):
        tmp, svc = make_service()
        try:
            session = svc.runtime.new_session('本地居民', 'protagonist',
                                              profile_id='riverport_local')
            story = svc.runtime.package(session['revision'])['story']
            hidden = [t for t in story['mechanics']['traits']['templates']
                      if t['visibility'] == 'hidden']
            self.assertTrue(hidden)
            surface = svc.runtime.surface(session)
            context = json.dumps(svc.runtime.context(session, 'player', '看账',
                                                     svc.preferences()), ensure_ascii=False)
            surface_text = json.dumps(surface, ensure_ascii=False)
            for template in hidden:
                self.assertNotIn(template['name'], context)
                self.assertNotIn(template['details']['mechanism'][:12], context)
                self.assertNotIn(template['name'], surface_text)
            # 公开特质（自己那条）应该看得到
            own = story['mechanics']['traits']['templates'][0]
            self.assertIn(own['name'], context)
            # 压力阈值、未发生的阶段与私有信息不得出现
            for leaked in ('at_hours', 'burst_54', 'convoy_lost', 'priority'):
                self.assertNotIn(leaked, context)
                self.assertNotIn(leaked, surface_text)
        finally:
            if tmp:
                tmp.cleanup()


class RiverportRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.svc = make_service()

    def tearDown(self):
        if self.tmp:
            self.tmp.cleanup()

    def test_local_route_reaches_saved_grain_ending(self):
        s = self.svc.runtime.new_session('本地居民', 'protagonist',
                                        profile_id='riverport_local')
        s = turn(self.svc, s, 'check_ledger')          # 记下账目的数
        if s['active']:
            s = turn(self.svc, s, 'pass_by')          # 同地点的街头小事
        s = move(self.svc, s, 'guild_hall')
        self.assertEqual(s['active']['node'], 'guild_commission')
        s = turn(self.svc, s, 'decline_commission')
        s = move(self.svc, s, 'upper_sluice')
        self.assertEqual(s['active']['node'], 'sluice_keeper')
        s = turn(self.svc, s, 'ask_keeper')
        s = wait_hours(self.svc, s, 9)                # 到二十四小时，洪水夜才开
        self.assertEqual(s['active']['node'], 'flood_night')
        s = turn(self.svc, s, 'keep_gate')
        self.assertTrue(s['flags']['grain_secured'])
        self.assertEqual(s['ending']['id'], 'ending_saved_grain')
        self.assertEqual(self.svc.runtime.surface(s)['ending']['kind'], 'saved')

    def test_traveller_route_reaches_opened_sluice_ending(self):
        s = self.svc.runtime.new_session('外来旅人', 'protagonist',
                                        profile_id='outside_traveller')
        s = turn(self.svc, s, 'read_notice')
        s = move(self.svc, s, 'south_shoal')
        s = turn(self.svc, s, 'walk_shoal')            # 绕路：旧纤道
        s = move(self.svc, s, 'upper_sluice')
        s = wait_hours(self.svc, s, 12)
        self.assertEqual(s['active']['node'], 'flood_night')
        s = turn(self.svc, s, 'open_sluice')
        self.assertEqual(s['ending']['id'], 'ending_opened_sluice')

    def test_apprentice_route_reaches_lost_ending_and_keeps_playing(self):
        s = self.svc.runtime.new_session('行会学徒', 'protagonist',
                                        profile_id='guild_apprentice')
        s = turn(self.svc, s, 'decline_commission')    # 拒接差事也不卡死
        s = move(self.svc, s, 'upper_sluice')
        self.assertEqual(s['active']['node'], 'sluice_keeper')
        s = turn(self.svc, s, 'leave_sluice')
        s = wait_hours(self.svc, s, 13)
        self.assertEqual(s['active']['node'], 'flood_night')
        s = turn(self.svc, s, 'abandon_convoy')
        self.assertEqual(s['ending']['id'], 'ending_lost_convoy')
        self.assertEqual(s['ending']['kind'], 'lost')
        # 失败后继续：走过两段路回到米市街，仍能进入后续事件
        s = move(self.svc, s, 'guild_hall')
        s = move(self.svc, s, 'market_row')
        self.assertIsNotNone(s['active'])
        node = s['active']['node']
        self.assertIn(node, ('stall_repair', 'aftermath', 'aftermath_rebuild'))
        ends = {'stall_repair': 'pass_by', 'aftermath': 'count_losses',
                'aftermath_rebuild': 'rebuild_stall'}
        s = turn(self.svc, s, ends[node])
        s = settle(self.svc, s)
        s = settle(self.svc, move(self.svc, s, 'ferry_landing'))
        s = settle(self.svc, move(self.svc, s, 'south_shoal'))
        self.assertEqual(s['location'], 'south_shoal')
        # 结局记录不被后续标记覆盖
        self.assertEqual(self.svc.store.session(s['id'])['ending']['id'],
                         'ending_lost_convoy')

    def test_exhausting_max_turns_does_not_invent_an_ending(self):
        s = self.svc.runtime.new_session('本地居民', 'protagonist',
                                        profile_id='riverport_local')
        for _ in range(9):
            if not s['active']:
                break
            s = turn(self.svc, s, message='我只是站着听雨', channel='thought')
        self.assertNotIn('ending', s)

    def test_no_network_is_used_offline(self):
        calls = []
        original = self.svc.provider.complete

        async def guard(*args, **kwargs):
            calls.append(args)
            raise AssertionError('离线模式不应该调用远程模型')

        self.svc.provider.complete = guard
        try:
            s = self.svc.runtime.new_session('本地居民', 'protagonist',
                                            profile_id='riverport_local')
            s = turn(self.svc, s, 'hear_price')
            self.assertEqual(s['local']['resources']['hands'], 2)
        finally:
            self.svc.provider.complete = original
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
