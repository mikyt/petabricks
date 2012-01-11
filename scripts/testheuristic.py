#!/usr/bin/python

import unittest
from learningframework import Heuristic, NeededHeuristic

class TestNeededHeuristic(unittest.TestCase):
    def test_derive_heuristic(self):
        needed = NeededHeuristic("NeededHeur", min_val=2, max_val=3)
        
        heur = needed.derive_heuristic("a+b")
        
        self.assertEqual(heur.name, needed.name)
        self.assertEqual(heur.min_val, needed.min_val)
        self.assertEqual(heur.max_val, needed.max_val)
        self.assertIsNone(heur.tooLow)
        self.assertIsNone(heur.tooHigh)
        self.assertIsNone(heur.uses)
        
class TestHeuristic(unittest.TestCase):
    def test_inf_max(self):
        h = Heuristic("TestHeur", "a+b", max_val="inf")
        
        self.assertEqual(h.name, "TestHeur")
        self.assertEqual(h.formula, "a+b")
        self.assertIsNone(h.tooLow)
        self.assertIsNone(h.tooHigh)        
        self.assertEqual(h.min_val, float("-inf"))
        self.assertEqual(h.max_val, float("inf"))
        
        expected = '<heuristic name="TestHeur" formula="a+b" />'
        self.assertEqual(str(h), expected)
        

    def test_inf_min(self):
        h = Heuristic("TestHeur", "a+b", min_val="-inf")
        
        self.assertEqual(h.name, "TestHeur")
        self.assertEqual(h.formula, "a+b")
        self.assertIsNone(h.tooLow)
        self.assertIsNone(h.tooHigh)        
        self.assertEqual(h.max_val, float("inf"))
        self.assertEqual(h.min_val, float("-inf"))
        
        expected = '<heuristic name="TestHeur" formula="a+b" />'
        self.assertEqual(str(h), expected)
        
        
    def test_basic(self):
        h = Heuristic("TestHeur", "a+b")

        expected = '<heuristic name="TestHeur" formula="a+b" />'
        self.assertEqual(h.name, "TestHeur")
        self.assertEqual(h.formula, "a+b")
        self.assertIsNone(h.tooLow)
        self.assertIsNone(h.tooHigh)        
        self.assertEqual(h.min_val, float("-inf"))
        self.assertEqual(h.max_val, float("inf"))
        self.assertEqual(str(h), expected)
        
    
    def test_derive_needed_heuristic(self):
        h = Heuristic("NeededHeur", formula="a+b", uses=5, tooLow=2, min_val=1,
                      max_val=4)
                      
        needed = h.derive_needed_heuristic()
        
        self.assertEqual(needed.name, "NeededHeur")
        self.assertEqual(needed.min_val, 1)
        self.assertEqual(needed.max_val, 4)
        
    def test_evolve(self):
        formula = "a+5"
        heur = Heuristic("Evolve", formula)
        
        heur.evolve()
        
        self.assertNotEqual(formula, heur.formula)
        
if __name__ == "__main__":
    unittest.main(verbosity=2)
