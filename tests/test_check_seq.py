# -*- coding: utf-8 -*-
"""判定 v2 公开结果的单调序号 ``check_seq``。

前端用「会话 id + check_seq」判断一条 ``last_check`` 是不是新检定（而不是比较内容），
所以后端必须保证：

* 每次真正产生检定结果（正常结算 / refused / 兜底意图的 v2 分支）序号加一；
* 序号存在 session 里，随事件快照回滚一起恢复；
* 没有 ``mechanics.checks`` 的旧包不出现该字段；
* 旧存档里没有序号的 ``last_check`` 仍能读取，下一条新检定从 1 开始。

全部在临时库里跑，不联网。
"""
import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import attributes, checks, free_actions
from app.contracts import Turn
from app.service import Service
from app.storage import Store
from tests import test_fallback_intent as fb
from tests.test_checks_v2 import Base
from tests.test_checks_v2_http import LegacyHttpTests


class SeqTests(Base):
    def seq_of(self, s):
        return s['last_check'].get('check_seq')

    def test_seq_increments_for_settled_and_refused_checks(self):
        s = self.reload()
        self.assertNotIn('check_seq', s)
        s = self.do('bully')                       # 社交底线拒绝：不掷骰也是一条新结果
        self.assertEqual(s['last_check']['tier'], 'refused')
        self.assertEqual(self.seq_of(s), 1)
        self.assertEqual(s['check_seq'], 1)
        s = self.do('bully', s)                    # 内容完全相同的第二次结果，序号不同
        self.assertEqual(self.seq_of(s), 2)
        s = self.do('pitch', s)                    # 正常结算
        self.assertNotEqual(s['last_check']['tier'], 'refused')
        self.assertEqual(self.seq_of(s), 3)
        s = self.do('sneak', s)
        self.assertEqual(self.seq_of(s), 4)
        self.assertEqual(s['check_seq'], 4)
        self.assertEqual(self.surface(s)['last_check']['check_seq'], 4)

    def test_surface_without_a_new_check_keeps_the_same_seq(self):
        s = self.do('pitch')
        first = self.surface(s)['last_check']['check_seq']
        self.assertEqual(self.surface(self.reload(s))['last_check']['check_seq'], first)
        s = self.do('leave', s)                    # 没有检定的动作不产生新序号
        self.assertEqual(s['check_seq'], first)

    def test_rollback_restores_the_counter(self):
        s = self.do('pitch')
        self.assertEqual(s['check_seq'], 1)
        s = self.do('leave', s)
        restored = self.rt.rollback(s, s['archives'][0]['id'])
        # 回到事件开始前的快照：计数器与快照一致（那时还没有检定）。
        self.assertEqual(restored.get('check_seq', 0), 0)
        self.assertNotIn('last_check', restored)
        again = self.do('pitch', self.reload(restored))
        self.assertEqual(self.seq_of(again), 1)

    def test_rollback_to_a_mid_game_snapshot_keeps_the_earlier_count(self):
        s = self.do('bully')
        s = self.do('bully', s)
        self.assertEqual(s['check_seq'], 2)
        snap = copy.deepcopy(self.rt.snapshot(s))
        s = self.do('pitch', s)
        self.assertEqual(s['check_seq'], 3)
        self.assertEqual(snap['check_seq'], 2)
        self.assertEqual(snap['last_check']['check_seq'], 2)

    def test_old_save_without_a_seq_reads_and_continues_from_one(self):
        s = self.do('bully')
        old = self.reload(s)
        old.pop('check_seq')
        old['last_check'].pop('check_seq')
        self.svc.store.save_session(old)
        surface = self.surface(self.reload(old))
        self.assertEqual(surface['last_check']['tier'], 'refused')
        self.assertNotIn('check_seq', surface['last_check'])
        s = self.do('bully', self.reload(old))
        self.assertEqual(self.seq_of(s), 1)

    def test_stamp_is_robust_to_bad_stored_values(self):
        for bad in (None, 'x', -3, 0, True, 1.5):
            session, row = {'check_seq': bad}, {}
            checks.stamp(session, row)
            self.assertEqual(row['check_seq'], 1)
            self.assertEqual(session['check_seq'], 1)
        session = {'check_seq': 7}
        self.assertEqual(checks.stamp(session, {})['check_seq'], 8)


class FallbackSeqTests(unittest.TestCase):
    """兜底意图的 v2 分支也要盖序号。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.svc = Service(Store(Path(self.tmp.name) / 'seq.sqlite3'), Path(self.tmp.name))
        self.svc.provider.configure({'offline': True})
        self.rt = self.svc.runtime
        story = fb.story_doc()
        story['mechanics']['attributes'] = attributes.specification()
        story['mechanics']['checks'] = {'version': 2, 'die': 'd20', 'display': 'transparent',
                                        'default_position': 'risky',
                                        'default_effect': 'standard'}
        self.rt.commit_package(story, fb.characters_doc(), '兜底序号')
        self.s = self.rt.new_session('兜底', 'protagonist')
        patch.object(self.svc.provider, 'complete',
                     side_effect=AssertionError('network call')).start()
        self.addCleanup(patch.stopall)

    def attempt(self):
        s = self.svc.store.session(self.s['id'])
        p = self.rt.package(s['revision'])
        node = self.rt.node(s) if s['active'] else None
        row = free_actions.suggest(s, p['story'], node, '仔细观察一下这条街',
                                   characters=p['characters'])['matched'][0]
        asyncio.run(self.svc.turn(s['id'], Turn(message='看', action_id=row['action_id'],
                                                confirm=row['confirm'])))
        return self.svc.store.session(s['id'])

    def test_fallback_v2_attempts_are_numbered(self):
        first = self.attempt()
        self.assertEqual(first['last_check']['check_seq'], 1)
        second = self.attempt()
        self.assertEqual(second['last_check']['check_seq'], 2)
        self.assertEqual(second['check_seq'], 2)
        self.assertEqual(self.rt.surface(second)['last_check']['check_seq'], 2)


class LegacySeqTests(LegacyHttpTests):
    def test_old_packages_never_get_a_check_seq(self):
        response = self.client.get('/api/sessions/' + self.session_id + '/confirm/pitch')
        payload = response.json()
        response = self.client.post('/api/sessions/' + self.session_id + '/chat',
                                    json={'message': '谈买卖', 'action_id': 'pitch',
                                          'confirm': payload['confirm']})
        self.assertEqual(response.status_code, 200, response.text)
        saved = self.svc.store.session(self.session_id)
        self.assertNotIn('check_seq', saved)
        self.assertNotIn('last_check', saved)
        surface = self.client.get('/api/sessions/' + self.session_id).json()
        self.assertNotIn('check_seq', str(surface))
        for row in saved['checks']:
            self.assertNotIn('check_seq', row)


# 不要把被继承的旧测试在本模块里再跑一遍。
del LegacyHttpTests


if __name__ == '__main__':
    unittest.main()
