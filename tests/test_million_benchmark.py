import copy
import unittest
from tools.million_context_benchmark import targets,grade,filler,POSITIONS
from tools.analyze_million_context import content_answer


class MillionBenchmarkTests(unittest.TestCase):
    def test_normalization_only_allows_named_prefixes(self):
        _,expected,_=targets(73101)
        answer=copy.deepcopy(expected)
        answer['chain']['receiver']=answer['chain']['receiver'].removeprefix('商人')
        answer['first_meal']['meat']='肉'+answer['first_meal']['meat']
        self.assertTrue(all(grade(content_answer(answer,expected),expected).values()))
        answer['first_meal']['meat']='肉不'+expected['first_meal']['meat']
        answer['p0']['code']='商人'+expected['p0']['code']
        normalized=grade(content_answer(answer,expected),expected)
        self.assertFalse(normalized['first_meal.meat'])
        self.assertFalse(normalized['p0.code'])
    def test_answer_not_missing_or_boolean_numeric_coercion(self):
        _,expected,_=targets(73101)
        self.assertTrue(all(grade(expected,expected).values()))
        altered=copy.deepcopy(expected)
        del altered['unknown']
        altered['p0']['verified']=0
        altered['chain']['sources'].reverse()
        checks=grade(altered,expected)
        self.assertFalse(checks['unknown'])
        self.assertFalse(checks['p0.verified'])
        self.assertFalse(checks['chain.sources'])

    def test_target_evidence_consistent_and_distributed(self):
        pools,expected,query=targets(73101)
        self.assertEqual(len(pools),len(POSITIONS))
        for i in range(5):
            self.assertIn(expected['p'+str(i)]['code'],'\n'.join(pools[i]))
            self.assertIn(expected['p'+str(i)]['source'],'\n'.join(pools[i]))
            self.assertNotIn(expected['p'+str(i)]['code'],query)
        corpus='\n'.join(x for p in pools for x in p)
        for source in expected['chain']['sources']:self.assertIn(source,corpus)
        self.assertEqual(targets(73101),targets(73101))
        self.assertNotEqual(targets(73101),targets(73102))
        self.assertEqual(filler(73101,2),filler(73101,2))
