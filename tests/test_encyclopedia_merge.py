# -*- coding: utf-8 -*-
"""归并工具（``tools/encyclopedia_merge.py``）：重合条目并到已有元素，而不是新建重复元素。

用户要求：「如果有重合的就在同一药材（美食）元素上添加对应词条」。本测试验的是
这条规则的工具侧：匹配归一化、只并允许的标签前缀、旧 schema 不加标签、不写错位置。

所有写入都在临时目录（把工具的 ROOT 指向副本），**不碰仓库里的真实源文件**。
"""
import json
import tempfile
import unittest
from pathlib import Path

from tools import encyclopedia_merge as merge

NS = {
    'schema_version': 1,
    'status': 'candidate',
    'sources': [{'id': 's1', 'title': '合成来源', 'access': 'read', 'supports': '自检'}],
}
SECTIONS = {
    'definition': '定义',
    'mechanism': '机制',
    'conditions': '条件',
    'exceptions': '例外',
    'story_uses': '用途',
    'historical_scope': '范围',
    'evidence_and_uncertainty': '证据',
}


def element(ident, name, aliases=(), tags=None, with_tags=True):
    body = {
        'id': ident,
        'name': name,
        'aliases': list(aliases),
        'summary': '概要 %s' % name,
        'category': 'life',
        'details': dict(SECTIONS, definition='定义 %s' % name),
        'source_ids': ['s1'],
        'review_status': 'needs_review',
        'detail_status': 'needs_detail',
    }
    if with_tags:
        body['tags'] = list(tags or ['kind:herb', 'tradition:western'])
    return body


class MergeKeyCase(unittest.TestCase):
    """名字比较要忽略括号限定语与空白，否则「胡椒（黑胡椒）」认不出「胡椒」。"""

    def test_parenthetical_qualifier_is_ignored(self):
        self.assertEqual(merge.merge_key('胡椒（黑胡椒）'), merge.merge_key('胡椒'))
        self.assertEqual(merge.merge_key('洋葱 (onion)'), '洋葱')

    def test_spacing_and_case_do_not_matter(self):
        self.assertEqual(merge.merge_key(' Black Pepper '), 'blackpepper')
        self.assertEqual(merge.merge_key('black pepper'), merge.merge_key('BLACKPEPPER'))

    def test_empty_and_non_string_are_safe(self):
        self.assertEqual(merge.merge_key(None), '')
        self.assertEqual(merge.merge_key(''), '')
        self.assertEqual(merge.merge_key('（）'), '')


class PlanCase(unittest.TestCase):
    """干跑计划：命中的进 merges，没命中的原样留下。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._saved_root = merge.ROOT
        merge.ROOT = self.root
        self.targets = ('docs/target.json',)
        (self.root / 'docs').mkdir(parents=True)
        self.write('docs/target.json', {
            **NS, 'group': 'target', 'elements': [
                element('t_pepper', '胡椒', ['黑胡椒']),
                element('t_legacy', '旧格式麦子', with_tags=False),
            ]})

    def tearDown(self):
        merge.ROOT = self._saved_root
        self.tmp.cleanup()

    def write(self, relative, payload):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def candidate(self, elements):
        path = self.root / 'candidate.json'
        path.write_text(json.dumps({**NS, 'group': 'cand', 'elements': elements},
                                   ensure_ascii=False, indent=2), encoding='utf-8')
        return path

    def test_overlap_is_merged_and_rest_stay(self):
        path = self.candidate([
            element('c_pepper', '胡椒（黑胡椒）'),
            element('c_new', '库里没有的草药'),
        ])
        group, merges, leftovers = merge.plan(path, 'story_uses', self.targets)
        self.assertEqual(group, 'cand')
        self.assertEqual([item['candidate']['id'] for item in merges], ['c_pepper'])
        self.assertEqual(merges[0]['target_id'], 't_pepper')
        self.assertEqual([item['id'] for item in leftovers], ['c_new'])

    def test_dry_run_writes_nothing(self):
        before = (self.root / 'docs/target.json').read_text(encoding='utf-8')
        path = self.candidate([element('c_pepper', '胡椒')])
        code = merge.main(['--candidate', str(path)], targets=self.targets)
        self.assertEqual(code, 0)
        self.assertEqual((self.root / 'docs/target.json').read_text(encoding='utf-8'), before)


class ApplyCase(unittest.TestCase):
    """真写入：追加【补充条目】、保留 merged_from、只并允许前缀的标签。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._saved_root = merge.ROOT
        merge.ROOT = self.root
        (self.root / 'docs').mkdir(parents=True)
        self.targets = ('docs/target.json',)
        self.write('docs/target.json', {
            **NS, 'group': 'target', 'elements': [
                element('t_pepper', '胡椒', ['黑胡椒'], tags=['kind:herb', 'tradition:eastern']),
                element('t_legacy', '旧格式麦子', with_tags=False),
            ]})

    def tearDown(self):
        merge.ROOT = self._saved_root
        self.tmp.cleanup()

    def write(self, relative, payload):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def run_candidate(self, elements, section='story_uses', keep=True):
        """默认附带一条不命中的条目：全部归并会被工具拒绝（防止写出空分区）。"""
        payload = list(elements)
        if keep:
            payload.append(element('c_keep', '待保留草药'))
        path = self.root / 'candidate.json'
        path.write_text(json.dumps({**NS, 'group': 'cand', 'elements': payload},
                                   ensure_ascii=False, indent=2), encoding='utf-8')
        return merge.main(['--candidate', str(path), '--section', section, '--apply'],
                          targets=self.targets)

    def target(self, ident):
        document = json.loads((self.root / 'docs/target.json').read_text(encoding='utf-8'))
        return [row for row in document['elements'] if row['id'] == ident][0]

    def test_supplement_block_lands_in_the_requested_section(self):
        self.assertEqual(self.run_candidate([element('c_pepper', '胡椒')]), 0)
        target = self.target('t_pepper')
        self.assertIn('【补充条目', target['details']['story_uses'])
        self.assertIn('cand', target['details']['story_uses'])
        self.assertEqual(target['merged_from'], ['cand/c_pepper'])
        # 原有分节不被清空或覆盖。
        self.assertEqual(target['details']['definition'], '定义 胡椒')

    def test_merging_twice_does_not_duplicate(self):
        self.run_candidate([element('c_pepper', '胡椒')])
        self.run_candidate([element('c_pepper', '胡椒')])
        target = self.target('t_pepper')
        self.assertEqual(target['merged_from'], ['cand/c_pepper'])
        self.assertEqual(target['details']['story_uses'].count('【补充条目'), 2)

    def test_only_retrieval_tags_are_merged(self):
        self.run_candidate([element('c_pepper', '胡椒', tags=[
            'kind:herb', 'tradition:western', 'part:fruit', 'role:apothecary_commodity',
            'effect:digestive', 'grade:common'])])
        tags = self.target('t_pepper')['tags']
        self.assertIn('part:fruit', tags)
        self.assertIn('role:apothecary_commodity', tags)
        self.assertIn('effect:digestive', tags)
        # 不能把第二个 tradition: 并进去（一个元素只取一个传统）。
        self.assertEqual([t for t in tags if t.startswith('tradition:')], ['tradition:eastern'])
        self.assertNotIn('grade:common', tags)

    def test_legacy_element_gets_no_tags(self):
        """旧 schema 的元素不会入库原生标签，所以不应该给它添上误导性的 tags 键。"""
        self.run_candidate([element('c_wheat', '旧格式麦子')])
        self.assertNotIn('tags', self.target('t_legacy'))
        self.assertIn('【补充条目', self.target('t_legacy')['details']['story_uses'])

    def test_alias_is_added_only_when_it_differs(self):
        """真有别名价值时加一条；归一化后与原名相同的就不重复加。"""
        self.run_candidate([element('c_pepper', '胡椒（黑胡椒）', aliases=['洋胡椒'])])
        aliases = self.target('t_pepper')['aliases']
        self.assertIn('洋胡椒', aliases)
        # 「胡椒（黑胡椒）」归一化后就是「胡椒」，不应再加一条几乎重复的别名。
        self.assertNotIn('胡椒（黑胡椒）', aliases)

    def test_merged_element_leaves_the_candidate_file(self):
        """真归并后，候选文件里不能再留着这条，否则入库就多一条重复元素。"""
        path = self.root / 'candidate.json'
        path.write_text(json.dumps({**NS, 'group': 'cand', 'elements': [
            element('c_pepper', '胡椒'), element('c_keep', '待保留草药')]},
            ensure_ascii=False, indent=2), encoding='utf-8')
        self.assertEqual(merge.main(['--candidate', str(path), '--apply'], targets=self.targets), 0)
        remaining = [row['id'] for row in
                     json.loads(path.read_text(encoding='utf-8'))['elements']]
        self.assertEqual(remaining, ['c_keep'])
        self.assertIn('【补充条目', self.target('t_pepper')['details']['story_uses'])

    def test_refuses_to_empty_the_candidate_file(self):
        """如果全部条目都被归并，宁可不写，也不弄出一份空分区。"""
        path = self.root / 'candidate.json'
        path.write_text(json.dumps({**NS, 'group': 'cand',
                                   'elements': [element('c_pepper', '胡椒')]},
                                   ensure_ascii=False, indent=2), encoding='utf-8')
        before = path.read_text(encoding='utf-8')
        with self.assertRaises(SystemExit):
            merge.main(['--candidate', str(path), '--apply'], targets=self.targets)
        self.assertEqual(path.read_text(encoding='utf-8'), before)

    def test_map_forces_a_specific_target_and_keeps_its_id(self):
        """--map 既要能改目标，也要在输出里保住候选 id（不能变成 None）。"""
        path = self.root / 'candidate.json'
        path.write_text(json.dumps({**NS, 'group': 'cand', 'elements': [
            element('c_pepper', '胡椒'), element('c_keep', '待保留草药')]},
            ensure_ascii=False, indent=2), encoding='utf-8')
        code = merge.main(['--candidate', str(path), '--apply',
                           '--map', 'c_pepper=docs/target.json#t_legacy'],
                          targets=self.targets)
        self.assertEqual(code, 0)
        self.assertIn('cand/c_pepper', self.target('t_legacy')['merged_from'])

    def test_skip_id_keeps_the_element_in_its_own_partition(self):
        """名似而实异（如「地龙」撞「龙」）靠 --skip-id 保住为正元素。"""
        path = self.root / 'candidate.json'
        path.write_text(json.dumps({**NS, 'group': 'cand', 'elements': [
            element('c_pepper', '胡椒')]}, ensure_ascii=False, indent=2), encoding='utf-8')
        code = merge.main(['--candidate', str(path), '--apply', '--skip-id', 'c_pepper'],
                          targets=self.targets)
        self.assertEqual(code, 0)
        remaining = [row['id'] for row in
                     json.loads(path.read_text(encoding='utf-8'))['elements']]
        self.assertEqual(remaining, ['c_pepper'])
        self.assertNotIn('【补充条目', self.target('t_pepper')['details']['story_uses'])


if __name__ == '__main__':
    unittest.main()
