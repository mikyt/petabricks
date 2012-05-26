"""Framework implementing long term learning of heuristics """
import random
import heuristicdb
import pprint
import logging
import mincemeat
import os.path
import time
from heuristic import (AvailableFeatures, Heuristic, HeuristicManager, 
                      HeuristicSet, NeededHeuristic)


logger = logging.getLogger(__name__)


#---------------- Config ------------------
CONF_MIN_TRIAL_NUMBER = 16
CONF_PICK_BEST_N = 10
NUM_ELITE_BEST= 1
NUM_ELITE_MOST_FREQUENT = 1
NUM_ELITE_BEST_SET = 1
NUM_GENERATIONS = 3
#------------------------------------------

def import_object(moduleName, objectName):
  module = __import__(moduleName)
  return getattr(module, objectName)
  
  
class Error(Exception):
    """Base class for all the exceptions thrown by the learning framework"""
    pass


class AllCandidatesCrashError(Error):
    pass

class MapReduceServerError(Error):
    pass

class RuntimeGeneratedFunctionError(Error):
    "The function was generated at runtime: it's not contained in any module"
    pass

class Candidate:
  """Represents a learning candidate. Objects can be considered candidate
if they have this set of attributes.
They do NOT need to inherit from this class"""
  def __init__(self, heuristicSet, failed, assignScores):
    if heuristicSet is None:
      self.heuristicSet = HeuristicSet()
    else:
      self.heuristicSet = heuristicSet

    self.failed = failed
    self.assignScores = assignScores
    self.originalIndex = None
    
  def _extra_repr(self):
    """Print all the fields that have been added to the candidate"""
    extra = []
    for key in self.__dict__:
        if key not in ['__doc__',
                       '__init__',
                       '__module__',
                       '__repr__',
                       '_extra_repr',
                       'assignScores',
                       'failed',
                       'heuristicSet',
                       'originalIndex']:
            extra.append("%s: %s" % (key, self.__dict__[key]))

    return "\n".join(extra)
    
  
  def __repr__(self):
    if self.failed:
      failed_str = "FAILED"
    else:
      failed_str = "Successful"
      
    return ("------------------------------------\n"
            "Candidate: %s\n"
            "  assignScores: %s\n"
            "  originalIndex: %s\n"
            "  Heuristic set: %s\n"
            "%s\n"
            "------------------------------------\n"
            ) % (failed_str,
                 self.assignScores,
                 self.originalIndex,
                 self.heuristicSet,
                 self._extra_repr())
					

class FailedCandidate(Candidate):
  """Represents a candidate that failed during compilation or tuning.
If assignScores is False, when this candidate is graded it's only marked as used
but not given any point (thus it is penalized)"""
  def __init__(self, heuristicSet = None, assignScores = True):
    Candidate.__init__(self, heuristicSet, failed=True, 
                       assignScores=assignScores)


class SuccessfulCandidate(Candidate):
  """Represents a candidate that was executed correctly"""
  def __init__(self, heuristicSet):
    Candidate.__init__(self, heuristicSet, failed=False, assignScores=True)        


class CandidateList(list):
  def __init__(self, sortingKey):
    self._sortingKey = sortingKey

    
  def __getstate__(self):
    state = self.__dict__.copy()
    del state["_sortingKey"]
    state["_sortingKey_module"] = self._sortingKey.__module__
    state["_sortingKey_name"] = self._sortingKey.__name__
    
    
  def __setstate__(self, state):
    self.__dict__.update(state)
    
    moduleName = state["_sortingKey_module"]
    del state["_sortingKey_module"]
    functionName = state["_sortingKey_name"]
    del state["_sortingKey_name"]
    
    self.__dict__["_sortingKey"] = import_object(moduleName, functionName)

  def sort(self):
    #Call sort() of "list"
    super(CandidateList, self).sort(key = self._sortingKey)

    

def _mapfn(count, job):
    benchmark = job["benchmark"]
    hset = job["hset"]
    additional_parameters = job["additional_parameters"]
    (testfn_module, testfn_name) = job["testfn"]
    
    #Import the function
    module = __import__(testfn_module)
    testfn = getattr(module, testfn_name)
    
    candidate = testfn(benchmark, count, hset, additional_parameters)
    candidate.originalIndex = count                                    
    yield "candidates", candidate
      
def _reducefn(_, value):
    return value


class Learner(object):
  _setup = None
  _testHSet = None
  _candidateSortingKey = None
  _tearDown = None
  
  def _getNeededHeuristics(self, unused_benchmark):
    return []
   
  def _get_available_features(self, unused_benchmark,
                              unused_heuristic_name=None):
      return []
  
  def __init__(self, heuristicSetFileName = None, 
               use_mapreduce = False, 
               min_trial_number=None,
               knowledge=None,
               generations=None):
    if generations == None:
        self.num_generations = NUM_GENERATIONS
    else:
        self.num_generations = generations
        
    self._heuristicManager = HeuristicManager(heuristicSetFileName)
    if min_trial_number:
        self._minTrialNumber = min_trial_number
    else:
        self._minTrialNumber = CONF_MIN_TRIAL_NUMBER
    self._db = heuristicdb.HeuristicDB(knowledge)

    self.use_mapreduce = use_mapreduce 
    
    if use_mapreduce:
        self._start_server()
                        
    hSetsFromFile = self._heuristicManager.allHeuristicSets()
    self._db.addAsFavoriteCandidates(hSetsFromFile, 2)

    random.seed()

    
  def _start_server(self, retries=10):
      self._server = mincemeat.Server()
      self._server.mapfn = _mapfn
      self._server.reducefn = _reducefn
      self._server.relaunch_map = False
      self._server.relaunch_reduce = False
      self._server.start()
      while self._server.initializing():
          #Wait for the server to be initialized
          pass
      
      if not self._server.initialized:
          #The server died without being initialized!!
          #Maybe it just couldn't bind to its TCP port
          logger.warning("MapReduce server initialization failed")
          self._server.close()
          
          if retries == 0:
              logger.error("Unable to start server")
              raise MapReduceServerError
          
          #Wait and retry
          logger.warning("Retrying in 10 seconds")
          time.sleep(10)
          self._start_server(retries-1)
          
      logger.info("MapReduce server initialized")
  
  def storeCandidatesDataInDB(self, candidates):
    """Store data from all the info file, with score.
The candidates should already be ordered (from the best one to the worst one)"""
    count = 0
    pp=pprint.PrettyPrinter()
    for candidate in candidates:
        h_set = candidate.heuristicSet
        logger.info("Storing this heuristic set:\n%s",
                    pp.pformat(h_set))

        if candidate.assignScores and not candidate.failed:
            points = candidate.speedup
            self._db.updateHSetWeightedScore(h_set, points)
        else:
            self._db.updateHSetWeightedScore(h_set, points=0, uses=1)


        count = count +1

  def _generateHSetsByElitism(self, neededHeuristics, eliteSize, 
                              get_n_heuristics):
    """Generate "eliteSize" heuristic sets by elitism, that is by
getting the current best heuristics, without modifying them"""

    allHSets = []
    heuristicLists = {}
    for heur in neededHeuristics:
        kind = heur.name
        heuristicLists[kind] = [heur.derive_heuristic(formula)
                                for (finalScore, formula)
                                in get_n_heuristics(kind, eliteSize)]

    #Build the sets
    try:
      for i in range(eliteSize):
	newSet = HeuristicSet()

	for heur in neededHeuristics:
              kind=heur.name
              newSet[kind] = heuristicLists[kind][i]

	allHSets.append(newSet)
	logger.debug("ELITE(%s): %s", get_n_heuristics.__name__, newSet)

    except IndexError:
      #One of the lists is too small: stop here
      pass

    return allHSets
 
 
  def _getBestHeuristicSubsets(self, neededHeuristics, N):
      """Return the N best sets of heuristics.
      They could be made by just a subset of the needed heuristics.
      N is a maximum limit. If not enough sets are available, less than N sets
      will be returned"""
      
      all_hsets = []
      scored_IDs = self._db.getNBestHeuristicSubsetID(neededHeuristics, N)
      
      for _, ID in scored_IDs:
          db_hset = self._db.getHeuristicSet(ID) 
          new_hset = db_hset.provide_formulas(neededHeuristics)
          all_hsets.append(new_hset)
          logger.debug("Subset from DB: %s", new_hset)
          
      return all_hsets
      
      
  
  def _test_with_mapreduce(self, benchmark, all_hsets, additional_parameters):
      testfn_import_data = get_function_import_data(self._testHSet)
      print testfn_import_data
      
      jobs = ({"benchmark" : benchmark,
               "hset" : hset,
               "additional_parameters" : additional_parameters,
               "testfn" : testfn_import_data}
              for hset in all_hsets )
              
      datasource = dict(enumerate(jobs))
      
      print "Waiting for mincemeat.py MapReduce workers"
      results = self._server.process_datasource(datasource)

      new_candidates = results["candidates"]
      additional_parameters["candidates"].extend(new_candidates)
  
  
  def _test_sequentially(self, benchmark, allHSets, additionalParameters):
      """Test sequentially all the heuristic sets on the benchmark, storing the
result inside the candidates list taken from the additional parameters"""
      candidates = additionalParameters["candidates"]
      
      testfn = self._testHSet
          
      count = 0
      for hSet in allHSets:
          currentCandidate = testfn(benchmark, count, hSet, 
                                    additionalParameters)
          currentCandidate.originalIndex = count
          candidates.append(currentCandidate)
          count = count + 1
      
  def _generateAndTestHSets(self, benchmark, additionalParameters):
    neededHeuristics = additionalParameters["neededHeuristics"]

    allHSets = []
    elite = []
    
    best_subsets = self._getBestHeuristicSubsets(neededHeuristics, NUM_ELITE_BEST_SET)
    for hset in best_subsets:
        #These are subsets of the needed heuristics: they might be incomplete!
        hset.complete(neededHeuristics, self._db, CONF_PICK_BEST_N)
        
    elite.extend(best_subsets)
    
    from_best = self._generateHSetsByElitism(neededHeuristics, NUM_ELITE_BEST, 
                                         self._db.getBestNHeuristics)
    elite.extend(from_best)
    
    from_most_frequent = self._generateHSetsByElitism(neededHeuristics, 
                                         NUM_ELITE_MOST_FREQUENT, 
                                         self._db.getNMostFrequentHeuristics)
    elite.extend(from_most_frequent)


    #Generate the remaining needed heuristic sets
    other_hsets = []
    numGenerated = len(elite)
    numNeeded = self._minTrialNumber - numGenerated
    best = self._getBestHeuristicSubsets(neededHeuristics, numNeeded)
    other_hsets.extend(best)
    
    #Generate the remaining needed (empty) heuristic sets
    numGenerated = len(elite) + len(other_hsets)
    numNeeded = self._minTrialNumber - numGenerated
    for _ in range(numNeeded):
      other_hsets.append(HeuristicSet())

    #Complete and evolve non-elite heuristic sets
    for hSet in other_hsets:
      hSet.complete(neededHeuristics, self._db, CONF_PICK_BEST_N)  
      hSet.evolve(self._get_available_features(benchmark))
      
    #Prepare the list of all hsets
    allHSets.extend(elite)
    allHSets.extend(other_hsets)
    
    #Ensure there are no duplicates
    count=0
    for hSet in allHSets:
      previousHSets = allHSets[:count]
      hSet.ensureUnique(previousHSets, self._get_available_features(benchmark))
      count = count + 1
      
    if self.use_mapreduce:
        self._test_with_mapreduce(benchmark, allHSets, additionalParameters)
    else:
        self._test_sequentially(benchmark, allHSets, additionalParameters)


  def use_learning(self, benchmark, learn=True):
      if not learn:
          return self.use_learning_on_one_generation(benchmark, learn)
          
      for generation in xrange(self.num_generations):
          logger.info("Testing generation %d/%d", generation+1, self.num_generations)
          result = self.use_learning_on_one_generation(benchmark, learn)
          if result != 0:
              return result
          
      return result
      
  def use_learning_on_one_generation(self, benchmark, learn=True):
    logger.info("Using best heuristics on: %s", benchmark)

    #Init variables
    candidates = CandidateList(self._candidateSortingKey)
    additionalParameters={}

    additionalParameters["candidates"] = candidates

    if self._setup is not None:
      result = self._setup(benchmark, additionalParameters)
      if result != 0:
        return result

    neededHeuristics = self._getNeededHeuristics(benchmark)
    additionalParameters["neededHeuristics"] = neededHeuristics
    logger.debug("Needed heuristics: %s", neededHeuristics)

    canLearn = (len(neededHeuristics) > 0)
    if canLearn:
        self._generateAndTestHSets(benchmark, additionalParameters)

        candidates.sort()

        pp = pprint.PrettyPrinter()
        logger.debug(pp.pformat(candidates))
    
        if candidates[0].failed:
            raise AllCandidatesCrashError

        if learn:
            logger.info("Storing learning results in the DB")
            self.storeCandidatesDataInDB(candidates)
    else:
        logger.info("Nothing to learn: no heuristic is needed")

    if self._tearDown is not None:
        self._tearDown(benchmark, additionalParameters)

    return 0

  def close(self):
      if hasattr(self, "_server"):
          self._server.close()


    
def get_function_module_name(function):
    """Return the name of the module containing the given function"""
    
    if function.__module__ != "__main__":
        return function.__module__
    
    #The function is defined inside this module itself!
    #What's my name?
    import __main__
    if not hasattr(__main__, "__name__"):
        raise RuntimeGeneratedFunctionError
    
    module_file_path = __main__.__file__
    module_file_name = os.path.basename(module_file_path)
    module_name = os.path.splitext(module_file_name)[0]
    return module_name
    
        
def get_function_import_data(function):
    """Return the pair (module, name) representing a function"""
    module = get_function_module_name(function)
    name = function.__name__
    
    return (module, name)
