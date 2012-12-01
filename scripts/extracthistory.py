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
        #Get the hsets the current one is derived from
        current_hset = self._db.getHeuristicSet(hset_id)
        history = [current_hset]
        while current_hset.isDerivedSet():
            next_id = current_hset.derivesFrom
            current_hset = self._db.getHeuristicSet(next_id)
            history.append(current_hset)
        
        #Get their heuristics in a dictionary of lists 
        #(one for every heuristic name)
        heur_history = {}
        for hset in history:
            for heur in hset.values():
                try:
                    one_history = heur_history[heur.name]
                except:
                    one_history = []
                    heur_history[heur.name] = one_history
                
                if len(one_history) > 0:
                    last_in_history = one_history[-1]
                    if heur != last_in_history:
                        one_history.append(heur)
                else:
                    one_history.append(heur)
                
        #For every heuristic name, continue the history backwards following the 
        #single heuristics
        for history in heur_history.values():
            last_in_history = history[-1]
            previous_history = self.get_heuristic_history(last_in_history)[1:]
            history.extend(previous_history)
            
        return heur_history

        
    def get_best_hset_history(self):
        [(_, hset_id)] = self._db.getNBestHeuristicSetID(1)
        
        return self.get_heuristic_set_history(hset_id)
        

def print_heur_history(history):
    for version in history:
        print version
        

def main(argv):
    hb = HistoryBuilder(argv[1]) 
    
    if len(argv) == 3:
        #History of the specified hset
        set_history = hb.get_heuristic_set_history(argv[2])
    else:
        #History of the best-scoring hset
        set_history = hb.get_best_hset_history()
    
    for heur_history in set_history.values():
        print_heur_history(heur_history)
        print
    
        
    
    
if __name__ == "__main__":
    main(sys.argv)