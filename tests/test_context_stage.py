import copy
import json
import unittest
from app.context_stage import stage_history
from app.contracts import Preferences
from app.prompts import context_json
from app.cache_metrics import cache_usage


class ContextStageTests(unittest.TestCase):
    def setUp(self):
        self.p=Preferences().model_dump()
        self.turns=[{'input':str(i),'reply':'记录'+str(i)+'；这只是传闻，尚未证实。','location':'旧城','event':'问路'} for i in range(22)]

    def test_append_boundary_and_rollback(self):
        a,summary,meta=stage_history(self.turns[:8],self.p)
        b,s2,m2=stage_history(self.turns[:9],self.p)
        self.assertEqual(b[:-1],a);self.assertEqual(summary,s2);self.assertEqual(meta,m2)
        selected,summary,meta=stage_history(self.turns[:17],self.p)
        self.assertEqual(selected,self.turns[16:17]);self.assertEqual(meta['start'],16)
        self.assertIn('尚未证实',summary)
        self.assertEqual(stage_history(self.turns[:8],self.p)[0],a)
        self.assertEqual(stage_history(self.turns[:18],self.p)[1],summary)

    def test_character_cap_and_sliding(self):
        rows=[{'input':str(i),'reply':'长句'*200} for i in range(12)]
        selected,_,meta=stage_history(rows,{**self.p,'stage_chars':1200})
        self.assertLessEqual(len(json.dumps(selected,ensure_ascii=False)),1250)
        self.assertGreater(meta['start'],0)
        selected,summary,_=stage_history(self.turns,{**self.p,'history_strategy':'sliding'})
        self.assertEqual(selected,self.turns[-6:]);self.assertEqual(summary,'')

    def test_scene_and_state_change_after_shared_history(self):
        a={'mode':'protagonist','last_summary':'','history':self.turns[:4],'location':'旧城','input':'你好'}
        b={**a,'history':self.turns[:5],'location':'新城','input':'走了'}
        prefix=context_json(a,'surface').split('],"location"')[0]
        self.assertTrue(context_json(b,'surface').startswith(prefix))
        self.assertEqual(json.loads(context_json(b,'surface')),b)

    def test_inner_request_and_example_do_not_precede_schema(self):
        c={'request':'生成陶碗','schema':{'type':'object'},'locations':[{'id':'b'},{'id':'a'}],'example':{'id':'generated_example'},'knowledge':[]}
        a=context_json(c,'inner');b=context_json({**c,'request':'生成铜杯'},'inner')
        self.assertEqual(a.split(',"request":')[0],b.split(',"request":')[0])
        self.assertTrue(a.startswith('{"schema"'))

    def test_usage_missing_is_unknown_and_nested_cache_supported(self):
        self.assertFalse(cache_usage({'prompt_tokens':100})['reported'])
        self.assertIsNone(cache_usage({})['miss_tokens'])
        m=cache_usage({'prompt_tokens':100,'prompt_tokens_details':{'cached_tokens':64},'completion_tokens':20})
        self.assertEqual(m['miss_tokens'],36);self.assertEqual(m['hit_rate'],.64)
        self.assertFalse(cache_usage({'prompt_tokens':100,'prompt_cache_hit_tokens':80,'prompt_cache_miss_tokens':50})['reported'])
