import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.drama import resolve_check,outcome_cues,cast_projection
from app.service import Service
from app.storage import Store
from app.contracts import Turn

ROOT=Path(__file__).resolve().parents[1]

class DramaTests(unittest.TestCase):
    def test_formula_determinism_bounds_and_validation(self):
        a=resolve_check('test','理解',.6,.55,.1)
        self.assertAlmostEqual(a['probability'],.53)
        self.assertEqual(a,resolve_check('test','理解',.6,.55,.1))
        self.assertEqual(resolve_check('s','力',1,0,0)['probability'],.95)
        self.assertEqual(resolve_check('s','力',0,1,1)['probability'],.05)
        for value in (float('nan'),2,True):
            with self.assertRaises(ValueError):resolve_check('s','力',value,.5,0)

    def test_keywords_do_not_mix_branches(self):
        a={'narrative_cues':{'success':['解除误会'],'failure':['歧义未解']}}
        self.assertEqual(outcome_cues(a,False,True)['keywords'],['歧义未解'])
        self.assertEqual(outcome_cues(a,True,True)['keywords'],['解除误会'])

    def test_runtime_effects_and_per_character_cues(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc=Service(Store(Path(tmp)/'test.sqlite3'),ROOT);rt=svc.runtime
            s=rt.new_session('分支测试','protagonist')
            request=Turn(message='收拾行装',action_id='pack')
            result=rt.prepare_turn(s,request);rt.finish_turn(s,request,'收起万言机。',result,{'calls':0})
            rt.move(s,'western_pass')
            package=rt.package(s['revision'])
            for success in (True,False):
                candidate=copy.deepcopy(s)
                with patch('app.runtime.resolve_check',return_value={'success':success,'probability':.53,'roll':.1 if success else .9}):
                    result=rt.prepare_turn(candidate,Turn(message='翻译',action_id='translate'))
                self.assertEqual(result['narrative']['result'],'success' if success else 'failure')
                self.assertTrue(candidate['flags']['translated' if success else 'needs_help'])
                self.assertNotIn('needs_help' if success else 'translated',candidate['flags'])
                self.assertEqual(result['reactions'][0]['character'],'pass_guard')
            s['characters']['oasis_merchant']['location']='western_pass'
            cast=cast_projection(package,s,['pass_guard','oasis_merchant'])
            self.assertEqual(len(cast),2)
            self.assertNotEqual(cast[0]['rhythm'],cast[1]['rhythm'])
            self.assertNotIn('secret',json.dumps(cast))
            self.assertEqual(len(cast_projection(package,s,['pass_guard','oasis_merchant'],'pass_guard')),1)
