#!/usr/bin/env python
"""Build the history of the heuristics of the best set in a DB

Receives the DB filename as the first parameter"""

import heuristicdb
import sys


class HistoryBuilder(object):    
    def __init__(self, db_path):
        self._db = heuristicdb.HeuristicDB(db_path)
    
        
    def get_heuristic_history(self, last_heuristic):
        history = [last_heuristic]
        
        current_heuristic = last_heuristic
        while current_heuristic.isDerivedHeuristic():
            next_id = current_heuristic.derivesFrom
            current_heuristic = self._db.getHeuristic(next_id)
            history.append(current_heuristic)
            
        return history
    
    
    def get_heuristic_set_history(self, hset_id):
        history = []
        
        hset = self._db.getHeuristicSet(hset_id)
        for heur in hset.values():
            history.append(self.get_heuristic_history(heur))
            
        return history

        
    def get_best_hset_history(self):
        [(_, hset_id)] = self._db.getNBestHeuristicSetID(1)
        
        return self.get_heuristic_set_history(hset_id)
        

def print_heur_history(history):
    for version in history:
        print version
        

def main(argv):
    hb = HistoryBuilder(argv[1]) 
    
    set_history = hb.get_best_hset_history()
    
    for heur_history in set_history:
        print_heur_history(heur_history)
        print
    
        
    
    
if __name__ == "__main__":
    main(sys.argv)