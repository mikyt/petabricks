#!/usr/bin/python

import unittest
from heuristic import Heuristic, HeuristicSet, NeededHeuristic
import formula

class TestNeededHeuristic(unittest.TestCase):
    def test_derive_heuristic(self):
        kind = "NeededHeur"
        
        features = ["a","b","c"] 
        
        needed = NeededHeuristic(kind, features, formula.IntegerResult, 
                                 min_val=2, max_val=3)
        
        heur = needed.derive_heuristic("a+b")
        
        self.assertEqual(heur.name, needed.name)
        self.assertEqual(heur.min_val, needed.min_val)
        self.assertEqual(heur.max_val, needed.max_val)
        self.assertIsNone(heur.tooLow)
        self.assertIsNone(heur.tooHigh)
        self.assertIsNone(heur.uses)
        
class TestHeuristic(unittest.TestCase):
    def test_inf_max(self):
        h = Heuristic("TestHeur", "a+b", formula.IntegerResult, max_val="inf")
        
        self.assertEqual(h.name, "TestHeur")
        self.assertEqual(h.formula, "a+b")
        self.assertIsNone(h.tooLow)
        self.assertIsNone(h.tooHigh)        
        self.assertEqual(h.min_val, float("-inf"))
        self.assertEqual(h.max_val, float("inf"))
        
        expected = '<heuristic name="TestHeur" formula="a+b" type="int" />'
        self.assertEqual(str(h), expected)
        

    def test_inf_min(self):
        h = Heuristic("TestHeur", "a+b", formula.DoubleResult, min_val="-inf")
        
        self.assertEqual(h.name, "TestHeur")
        self.assertEqual(h.formula, "a+b")
        self.assertIsNone(h.tooLow)
        self.assertIsNone(h.tooHigh)        
        self.assertEqual(h.max_val, float("inf"))
        self.assertEqual(h.min_val, float("-inf"))
        
        expected = '<heuristic name="TestHeur" formula="a+b" type="double" />'
        self.assertEqual(str(h), expected)
        
        
    def test_basic(self):
        h = Heuristic("TestHeur", "a+b", formula.IntegerResult)

        expected = '<heuristic name="TestHeur" formula="a+b" type="int" />'
        self.assertEqual(h.name, "TestHeur")
        self.assertEqual(h.formula, "a+b")
        self.assertEqual(h.resulttype, formula.IntegerResult)
        self.assertIsNone(h.tooLow)
        self.assertIsNone(h.tooHigh)        
        self.assertEqual(h.min_val, float("-inf"))
        self.assertEqual(h.max_val, float("inf"))
        self.assertEqual(str(h), expected)
        
    
    def test_derive_needed_heuristic(self):
        kind = "NeededHeur"
        h = Heuristic(kind, formula="a+b", 
                      resulttype=formula.IntegerResult, uses=5, tooLow=2, 
                      min_val=1, max_val=4)
                      
        features = ["a","b","c"] 
        needed = h.derive_needed_heuristic(features)
        
        self.assertEqual(needed.name, "NeededHeur")
        self.assertEqual(needed.min_val, 1)
        self.assertEqual(needed.max_val, 4)
        
    def test_evolve(self):
        formulastr = "a+5"
        kind = "Evolve"
        heur = Heuristic(kind, formulastr, formula.IntegerResult)
        
        features = ["a","b","c"]
        
        heur.evolve(features)
        
        self.assertNotEqual(formula, heur.formula)
        
    def test_boolean(self):
        h = Heuristic("SomeKind", "true", formula.BooleanResult)
        
        self.assertEqual(h.name, "SomeKind")
        self.assertEqual(h.formula, "true")
        self.assertEqual(h.resulttype, formula.BooleanResult)

        
class TestHeuristicSet(unittest.TestCase):
    def test_strings(self):
        h1 = Heuristic("Kind1", "a", formula.IntegerResult)
        h2 = Heuristic("Kind2", "b", formula.DoubleResult)
        h3 = Heuristic("Kind3", "true", formula.BooleanResult)
        
        hset = HeuristicSet()
        hset[h1.name] = h1
        hset[h2.name] = h2
        hset[h3.name] = h3
        
        self.assertEqual(hset.toXmlStrings(), ['<heuristic name="Kind3" formula="true" type="bool" />',
                                               '<heuristic name="Kind2" formula="b" type="double" />',
                                               '<heuristic name="Kind1" formula="a" type="int" />'])
                                               
if __name__ == "__main__":
    unittest.main(verbosity=2)
