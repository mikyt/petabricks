#!/usr/bin/python

import unittest
import formula
import os
from heuristicdb import HeuristicDB, KindNotFoundError
from heuristic import Heuristic, HeuristicSet, NeededHeuristic

DBFILENAME = "__testheuristicdb__.db"

def prefixed(name, prefix=None):
    if prefix:
        return prefix+"_"+name
    return name
    
class TestHeuristic(unittest.TestCase):
    db = None
    
    def setUp(self):
        if os.path.isfile(DBFILENAME):
            os.remove(DBFILENAME)
        self.db = HeuristicDB(DBFILENAME)
        self.assertIsNotNone(self.db)

        
    def tearDown(self):
        if os.path.isfile(DBFILENAME):
            os.remove(DBFILENAME)
            

            
    def _insertSampleHeuristics(self, prefix=""):
        #Use count of these heuristics is automatically set to 1
        h=Heuristic(prefixed("KindA", prefix), "a+b", formula.IntegerResult) 
        self.db.increaseHeuristicScore(h, 2)
        
        h=Heuristic(prefixed("KindA", prefix), "a+b+c", formula.IntegerResult)
        self.db.increaseHeuristicScore(h, 2)
        
        h=Heuristic(prefixed("KindB", prefix), "x+y+z", formula.IntegerResult)
        self.db.increaseHeuristicScore(h, 2)
    
    def _insertSampleHeuristicSet(self, prefix=""):
        hset = HeuristicSet()
       
        name = prefixed("KindA", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
       
        name=prefixed("KindB", prefix)
        heur = Heuristic(name, "x+y", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindC", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        self.db.updateHSetWeightedScore(hset, points=5)
        
        
        
    def _createSampleHSet(self, prefix=""):
        hset = HeuristicSet()
       
        name = prefixed("KindA", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
       
        name=prefixed("KindB", prefix)
        heur = Heuristic(name, "x+y", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindC", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindD", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindE", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindF", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindG", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindH", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindI", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindJ", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
        
        name = prefixed("KindK", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
       
        name = prefixed("KindL", prefix)
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=2,
                         tooLow=0, tooHigh=0)
        hset[name] = heur
       
        return hset
       
       
       
       
    def test_updateHSetWeightedScore(self):
        self._insertSampleHeuristics()
        
        hset = self._createSampleHSet()
        
        self.db.updateHSetWeightedScore(hset, points=5)
        
        
        heuristics = self.db.getHeuristicsScoreByKind("KindA", bestN=1)
        
        score = heuristics["a+b"]
        self.assertEqual(score, 4)
        
        heuristics = self.db.getHeuristicsScoreByKind("KindB", bestN=1)
        score = heuristics["x+y"]
        self.assertEqual(score, 5)
    
    def test_getHeuristicKindID_cache(self):
        prefix = "cache"
        self._insertSampleHeuristics(prefix)
        
        uncachedkindA = self.db.getHeuristicKindID(prefixed("KindA", prefix))
        uncachedKindB = self.db.getHeuristicKindID(prefixed("KindB", prefix))
        cachedkindA = self.db.getHeuristicKindID(prefixed("KindA", prefix))
        cachedkindB = self.db.getHeuristicKindID(prefixed("KindB", prefix))
        
        self.assertEqual(uncachedkindA, cachedkindA)
        self.assertEqual(uncachedKindB, cachedkindB)
        self.assertNotEqual(uncachedkindA, uncachedKindB)
    
    def test_getHeuristicKindID(self):
        self._insertSampleHeuristics()
        
        self.assertEqual(1, self.db.getHeuristicKindID("KindA"))
        self.assertRaises(KindNotFoundError, 
                          self.db.getHeuristicKindID, "KindZ")
        
        
    def test_getKindsList(self):
        prefix = "kindlist"
        self._insertSampleHeuristics(prefix)
        
        neededheuristics = []
        neededheuristics.append(NeededHeuristic(prefixed("KindA", prefix), [], 
                                                formula.IntegerResult))
        neededheuristics.append(NeededHeuristic(prefixed("KindB", prefix), [], 
                                                formula.IntegerResult))
                                                
        kindA = self.db.getHeuristicKindID(prefixed("KindA", prefix))
        kindB = self.db.getHeuristicKindID(prefixed("KindB", prefix))
        
        kindslist = self.db._getKindsList(neededheuristics)
        oraclekindslist = [kindA, kindB]
        self.assertEqual(kindslist, oraclekindslist)
        
        #Test returning a subset of the IDs since not all of the required ones
        #actually exist
        neededheuristics.append(NeededHeuristic(prefixed("KindZ", prefix), [], 
                                                formula.IntegerResult))
        kindslist = self.db._getKindsList(neededheuristics)
        self.assertEqual(kindslist, oraclekindslist)
        
    def test_getSQLKindsList(self):
        prefix = "SQLkindlist"
        self._insertSampleHeuristics(prefix)
        
        neededheuristics = []
        
        SQLKindslist0 = self.db._getSQLList(self.db._getKindsList(neededheuristics))
        oracleSQLkindslist0 = "()"
        self.assertEqual(SQLKindslist0, oracleSQLkindslist0)
        
        
        neededheuristics.append(NeededHeuristic(prefixed("KindA", prefix), [], 
                                                formula.IntegerResult))
        kindA = self.db.getHeuristicKindID(prefixed("KindA", prefix))
        
        SQLKindslist1 = self.db._getSQLList(self.db._getKindsList(neededheuristics))
        oracleSQLkindslist1 = "(%d)" % (kindA)
        self.assertEqual(SQLKindslist1, oracleSQLkindslist1)
                                                        
        neededheuristics.append(NeededHeuristic(prefixed("KindB", prefix), [], 
                                                formula.IntegerResult))
        kindB = self.db.getHeuristicKindID(prefixed("KindB", prefix))
        
        SQLKindslist2 = self.db._getSQLList(self.db._getKindsList(neededheuristics))
        oracleSQLkindslist2 = "(%d, %d)" % (kindA, kindB)
        self.assertEqual(SQLKindslist2, oracleSQLkindslist2)
        
        
    def test_getHeuristicSubsetsIDs(self):
        prefix="subsetID"
        self._insertSampleHeuristicSet(prefix)
        
        neededheuristics = []
        found = self.db.getHeuristicSubsetsIDs(neededheuristics)
        self.assertEqual(len(found), 0)
        
        neededheuristics.append(NeededHeuristic(prefixed("KindA", prefix), [], 
                                                formula.IntegerResult))
        found1 = self.db.getHeuristicSubsetsIDs(neededheuristics)
        self.assertEqual(len(found1), 0)
        
        neededheuristics.append(NeededHeuristic(prefixed("KindB", prefix), [], 
                                                formula.IntegerResult))
        found2 = self.db.getHeuristicSubsetsIDs(neededheuristics)
        self.assertEqual(len(found2), 0)
        
        neededheuristics.append(NeededHeuristic(prefixed("KindC", prefix), [], 
                                                formula.IntegerResult))
        found3 = self.db.getHeuristicSubsetsIDs(neededheuristics)
        self.assertEqual(len(found3), 1)
        
    def test_getHeuristicSet(self):
        hset = self._createSampleHSet()
        
        self.db.updateHSetWeightedScore(hset, points=5)
        
        #The ID is surely 1, because it's the only set in the DB
        retrieved = self.db.getHeuristicSet(1)
        
        for heuristic in hset.itervalues():
            corresponding = retrieved[heuristic.name]
            self.assertIsNotNone(corresponding)
            self.assertEqual(heuristic.formula, corresponding.formula)
            self.assertEqual(heuristic.resulttype, corresponding.resulttype)
        
    def test_getNBestHeuristicSubsetID(self):
        #Create Hset
        hset1 = HeuristicSet()
       
        name = "KindA"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=1, tooLow=0, 
                         tooHigh=0)
        hset1[name] = heur
        
        name = "KindB"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=1, tooLow=0, 
                         tooHigh=0)
        hset1[name] = heur
        
        
        hset2 = HeuristicSet()
        
        name = "KindA"
        heur = Heuristic(name, "c+d", formula.IntegerResult, uses=1, tooLow=0, 
                         tooHigh=0)
        hset2[name] = heur
        
        name = "KindB"
        heur = Heuristic(name, "e+f", formula.IntegerResult, uses=1, tooLow=0,
                         tooHigh=0)
        hset2[name] = heur
        
        
        hset3 = HeuristicSet()
        
        name = "KindA"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=1, tooLow=0,
                         tooHigh=0)
        hset3[name] = heur
        
        name = "KindB"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=1, tooLow=0, 
                         tooHigh=0)
        hset3[name] = heur
        
        name = "KindC"
        heur = Heuristic(name, "a+b", formula.IntegerResult, uses=1, tooLow=0,
                         tooHigh=0)
        hset3[name] = heur
        
        #Add sets to the DB
        self.db.updateHSetWeightedScore(hset1, points=2)
        self.db.updateHSetWeightedScore(hset2, points=4)
        self.db.updateHSetWeightedScore(hset3, points=5)
        
        
        #Verify
        needed1 = []
        needed1.append(NeededHeuristic("KindA", [], formula.IntegerResult))
        needed1.append(NeededHeuristic("KindB", [], formula.IntegerResult))
        
        result = self.db.getNBestHeuristicSubsetID(needed1, N=2)
        self.assertEqual(result, [(4, 2), (2, 1)])
        
        result = self.db.getNBestHeuristicSubsetID(needed1, N=2, threshold=3)
        self.assertEqual(result, [(4, 2)])
        
        result = self.db.getNBestHeuristicSubsetID(needed1, N=2, threshold=4)
        self.assertEqual(result, [(4, 2)])
        
        
        needed2 = []
        needed2.append(NeededHeuristic("KindC", [], formula.IntegerResult))
        
        result = self.db.getNBestHeuristicSubsetID(needed2, N=2)
        self.assertEqual(result, [])
        
    def test_markAsUsed(self):
        #Should be able to work also on a never defined before heuristic set
        hset = self._createSampleHSet()
        
        self.db.markAsUsed(hset, uses=1)
        
        retrieved = self.db.getHeuristicSet(1)
        
        self.assertEqual(len(hset), len(retrieved))
        for name in hset:
            origH = hset[name]
            retrH = retrieved[name]
            
            self.assertEqual(origH.name, retrH.name)
            self.assertEqual(origH.formula, retrH.formula)
            self.assertEqual(origH.resulttype, retrH.resulttype)
            
if __name__ == "__main__":
    unittest.main(verbosity=2)
