#!/usr/bin/python

import unittest
import formula
import os
import time
from heuristicdb import HeuristicDB
from heuristic import Heuristic, HeuristicSet

DBFILENAME = "__testheuristicdb__.db"

class TestHeuristic(unittest.TestCase):
    db = None
    
    def setUp(self):
        if os.path.isfile(DBFILENAME):
            os.remove(DBFILENAME)
        self.db = HeuristicDB(DBFILENAME)
        self.assertIsNotNone(self.db)

    
    def _insertSampleHeuristics(self):
        #Use count of these heuristics is automatically set to 1
        self.db.increaseHeuristicScore("KindA", "a+b", 2)
        self.db.increaseHeuristicScore("KindA", "a+b+c", 2)
    
    def _createSampleHSet(self, prefix=""):
        hset = HeuristicSet()
       
        name = prefix+"KindA"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
       
        name=prefix+"KindB"
        heur = Heuristic(name, "x+y", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindC"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindD"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindE"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindF"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindG"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindH"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindI"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindJ"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefix+"KindK"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
       
        name = prefix+"KindL"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
       
        return hset
       
       
       
       
    def test_updateHSetWeightedScore(self):
        self._insertSampleHeuristics()
        
        hset = self._createSampleHSet()
        
        start = time.time()
        self.db.updateHSetWeightedScore(hset, points=5)
        end = time.time()
        
        print "Time updateHSetWeightedScore: %f" % (end-start)
        
        
        heuristics = self.db.getHeuristicsScoreByKind("KindA", bestN=1)
        
        score = heuristics["a+b"]
        self.assertEqual(score, 4)
        
        heuristics = self.db.getHeuristicsScoreByKind("KindB", bestN=1)
        score = heuristics["x+y"]
        self.assertEqual(score, 5)
        
if __name__ == "__main__":
    unittest.main(verbosity=2)
