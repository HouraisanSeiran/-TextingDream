# -*- coding: utf-8 -*-
"""context 裁剪契约：键保留/缺键、级联优先级、dict 块整条裁剪、绝不切句。

背景：本轮曾把 `trim_context` 改成「容器空了就删键」，导致事件摘要回归
（`trimmed['dialogue_knowledge']`）在旧包上 KeyError。这里把两条契约钉住：

* 基线列表块（`TRIM_LIST_KEYS`）总是存在；
* 新机制块（压力/特质/元素清单）旧包不该有——缺键就保持缺键。
"""
import copy
import unittest

from app.runtime import TRIM_LIST_KEYS, TRIM_ORDER, chars, trim_context


BASE = {
    'dialogue_knowledge': [{'summary': '模型派生的叙述' * 40, 'status': '对话所闻，未独立核实'}],
    'recalled_dialogue': [{'input': '问', 'reply': '答' * 120}],
    'history': [{'input': '甲', 'reply': '乙'}],
    'memories': [{'text': '所闻' * 60}],
    'elements': [{'mark': '物' * 80}],
    'knowledge': [{'id': 'k1', 'content': '世界正典' * 60}],
    'last_summary': '【事件】某事\n【已确认】确认过的事（record:1）\n【原文】玩家：问 / 回应：答（turn:x:0）',
}


def without(**drop):
    data = copy.deepcopy(BASE)
    for key in drop:
        data.pop(key, None)
    return data


def trimmed(data, budget):
    return trim_context(copy.deepcopy(data), budget)


class TrimContractCase(unittest.TestCase):
    def test_old_package_never_gains_new_mechanic_keys(self):
        """没有压力/特质/元素块的旧包：裁剪不得凭空插入这三个键。"""
        data = without()
        for key in ('current_pressure', 'current_traits', 'current_elements'):
            self.assertNotIn(key, data)
            self.assertNotIn(key, TRIM_ORDER[:3], '新块必须排在基线块之后')
        result = trimmed(data, chars(data) - 50)
        for key in ('current_pressure', 'current_traits', 'current_elements'):
            self.assertNotIn(key, result)

    def test_baseline_list_keys_are_kept_even_when_empty(self):
        tight = chars({k: [] for k in TRIM_LIST_KEYS}) + 120
        result = trimmed(BASE, tight)
        for key in TRIM_LIST_KEYS:
            self.assertIn(key, result, key)
        self.assertEqual(result['dialogue_knowledge'], [])
        self.assertLessEqual(chars(result), tight)

    def test_dialogue_is_dropped_before_world_canon(self):
        data = without()
        budget = chars({**data, 'dialogue_knowledge': []}) + 5
        result = trimmed(data, budget)
        self.assertEqual(result['dialogue_knowledge'], [])
        self.assertEqual(result['knowledge'], data['knowledge'])
        self.assertEqual(result['recalled_dialogue'], data['recalled_dialogue'])
        self.assertEqual(result['last_summary'], data['last_summary'])

    def test_cascade_reaches_knowledge_last(self):
        data = without()
        bare = {key: [] for key in TRIM_LIST_KEYS}
        bare['last_summary'] = data['last_summary']
        # 刚够装下「什么都不剩但摘要还在」：知识库必须是被最后清掉的那块
        budget = chars(bare) + 5
        result = trimmed(data, budget)
        self.assertEqual(result['knowledge'], [])
        for key in TRIM_LIST_KEYS:
            self.assertEqual(result[key], [], key)
        self.assertEqual(result['last_summary'], data['last_summary'])

    def test_dict_blocks_are_dropped_whole(self):
        data = without()
        data['current_traits'] = {
            'basis': '特质是作者写的解释，不是数值',
            'items': [{'who': '守闸人', 'name': '固执'},
                      {'who': '掌柜', 'name': '守信'},
                      {'who': '船夫', 'name': '说数'}]}
        data['current_pressure'] = {'basis': '只有已知的消息', 'items': [{'text': '水位涨了'}]}
        # 预算降到只装得下基线块时，两个 dict 块必须整条消失，而不是留下半条
        bare = {key: [] for key in TRIM_LIST_KEYS}
        bare['last_summary'] = data['last_summary']
        result = trimmed(data, chars(bare) + 5)
        self.assertNotIn('current_traits', result)
        self.assertNotIn('current_pressure', result)
        for key in TRIM_LIST_KEYS:
            self.assertEqual(result[key], [], key)
            self.assertIn(key, result)

    def test_dict_block_entries_are_never_sliced(self):
        data = without(dialogue_knowledge=True, recalled_dialogue=True, history=True,
                       memories=True, elements=True, knowledge=True)
        items = [{'who': '守闸人', 'name': '固执', 'cue': 'x' * 200} for _ in range(3)]
        data['current_traits'] = {'basis': '边界', 'items': copy.deepcopy(items)}
        one_item = copy.deepcopy(data)
        one_item['current_traits']['items'] = items[:1]
        # 预算只装得下一个条目：多出来的必须整条丢掉，不能刮半句
        result = trimmed(data, chars(one_item) + 2)
        block = result.get('current_traits')
        if block is None:
            self.assertLessEqual(chars(result), chars(one_item) + 2)
        else:
            kept = block['items']
            self.assertLess(len(kept), len(items))
            self.assertEqual(kept, items[:len(kept)], '只允许整条丢弃，不能改写或切句')

    def test_last_summary_drops_prose_before_the_whole_line(self):
        data = without(dialogue_knowledge=True, recalled_dialogue=True, history=True)
        summary = data['last_summary']
        two_lines = '\n'.join(summary.split('\n')[:2])
        bare = {key: [] for key in TRIM_LIST_KEYS}
        bare['last_summary'] = two_lines
        # 预算介于「去掉原文段」与「完整摘要」之间：必须丢原文段，不丢确认记录
        result = trimmed(data, chars(bare) + 5)
        self.assertNotIn('【原文】', result['last_summary'])
        self.assertIn('【已确认】', result['last_summary'])


if __name__ == '__main__':
    unittest.main()
