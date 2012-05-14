#!/usr/bin/env python

import heuristicdb
import logging
import mylogger
import sys
import os
import pprint
import maximaparser

from optparse import OptionParser

NEUTRALITY_THRESHOLD = 0.90

logger = logging.getLogger(__name__)
pprinter = pprint.PrettyPrinter()

def parseCmdline():
    parser = OptionParser(usage="usage: learninggcctester.py [options] database(s)")
    #parser.add_option("--resultfile",
                      #type="string",
                      #help="file containing the results in gnuplot-compatible format",
                      #default="training-results.dat")
    parser.add_option("--logfile",
                      type="string",
                      help="file containing the log of errors",
                      default="log.dat")
    return parser.parse_args()



class AggregatedHeuristic(object):
    def __init__(self):
        self.true = 0
        self.false = 0
        self.formula = 0
    
    def __repr__(self):    
        data = {"TRUE":self.true, "FALSE":self.false, "FORMULA":self.formula}
        mode_str = max(data,key=data.get)
        
        if mode_str != "FORMULA":
            neutrality_level = 1 - abs(((self.true+1.0) - (self.false+1.0)) / (self.false+1.0))
            if neutrality_level > NEUTRALITY_THRESHOLD:
                mode_str = "NEUTRAL"
        
    
        return "%s -- true: %d, false: %d, formula: %d" % (mode_str,
                                                           self.true,
                                                           self.false,
                                                           self.formula)
        
    def count_true(self):
        self.true = self.true + 1
    
    def count_false(self):
        self.false = self.false + 1
        
    def count_formula(self):
        self.formula = self.formula + 1
        
        
        
class DBAnalyzer(object):
    def __init__(self, dbfilenames):
        self.dbs = []
        
        for filename in dbfilenames:
            newdb = heuristicdb.HeuristicDB(filename)
            newdb.filename = filename
            self.dbs.append(newdb)
        
    def printBestHeuristicSet(self, i):
        (best_score, best_id) = self.dbs[i].getNBestHeuristicSetID(1)[0]
        best_hset = self.dbs[i].getHeuristicSet(best_id)
        
        print "Best hset:"
        print best_hset
        print "Score: %f" % best_score
        
        
    def compute_aggregated_results(self):
        aggregated_results = {}
        for currentdb in self.dbs:
            self._aggregate_data_from_db(aggregated_results, currentdb)
        return aggregated_results
        
        
    def _aggregate_data_from_db(self, aggregated_results, currentdb):
        logger.info("Aggregating data from %s", currentdb.filename)
        best_id_list = currentdb.getNBestHeuristicSetID(1)
        
        if len(best_id_list) < 1:
            logger.warning("No best heuristic set in file %s", currentdb.filename)
            return 
            
        best_id = best_id_list[0][1]
        best_hset = currentdb.getHeuristicSet(best_id)
        
        for heuristic_name in best_hset:
            if heuristic_name not in aggregated_results:
                aggregated_results[heuristic_name] = AggregatedHeuristic()
                
            heuristic = best_hset[heuristic_name]
            
            if heuristic.formula == "true":
                aggregated_results[heuristic_name].count_true()
                continue
            
            if heuristic.formula == "false":
                aggregated_results[heuristic_name].count_false()
                continue
            
            #Apparently a formula
            try:
                result = heuristic.evaluate({})
                
                if result == True:
                    aggregated_results[heuristic_name].count_true()
                    continue
                
                if result == False:
                    aggregated_results[heuristic_name].count_false()
                    continue
                
                #Really a formula
                aggregated_results[heuristic_name].count_formula()
            except NameError:
                #Contains variables: really a formula!
                aggregated_results[heuristic_name].count_formula()
            
            
        
def main():
  """The body of the program"""

  (options, args) = parseCmdline()

  if len(args)==0:
    print "No test program specified"
    exit(-1)

  mylogger.configureLogging(options.logfile)

  dbfilenames = map(os.path.abspath, args)
 
  dbanalizer = DBAnalyzer(dbfilenames)
 
  results = dbanalizer.compute_aggregated_results()
  
  pprinter.pprint(results)
  
 
if __name__ == "__main__":
    main()
