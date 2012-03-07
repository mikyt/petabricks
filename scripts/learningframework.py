"""Framework implementing long term learning of heuristics """
import random
import advancedrandom
import xml.dom.minidom
import maximaparser
import heuristicdb
import copy
import pprint
import logging
import mincemeat
import formula
import os.path
import time
from xml.sax.saxutils import escape


logger = logging.getLogger(__name__)


#---------------- Config ------------------
CONF_MIN_TRIAL_NUMBER = 16
CONF_EXPLORATION_PROBABILITY = 0.3
CONF_PICK_BEST_N = 10
NUM_ELITE_BEST= 1
NUM_ELITE_MOST_FREQUENT = 1
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


class NeededHeuristic(object):
    def __init__(self, name, available_features, resulttype, min_val=None, max_val=None):
        assert name is not None
        assert available_features is not None
        self.name = name
        self.available_features = available_features
        self.resulttype = resulttype
        
        if min_val is None:
            self._min_val = float("-inf")
        else:
            self._min_val = min_val
        
        if max_val is None:
            self._max_val = float("inf")
        else:
            self._max_val = max_val
    
    def __repr__(self):
        return "%s %s (min=%s, max=%s)" % (self.resulttype, self.name, self.min_val, self.max_val)
        
        
    @property
    def min_val(self):
        return self._min_val
    
    @property
    def max_val(self):
        return self._max_val
     
    def derive_heuristic(self, formula):
        return Heuristic(self.name, formula, self.resulttype, 
                         min_val=self.min_val, max_val=self.max_val)
        
        
class Heuristic(object):
  def __init__(self, name, formula, resulttype, uses=None, tooLow=None, tooHigh=None, 
               min_val=None, max_val=None):
    self._name = name
    self._formula = formula
    self.resulttype = resulttype

    if (uses is None) or uses=="":
      self._uses=None
    else:
      self._uses = int(uses)

    if (tooLow is None) or tooLow=="":
      self._tooLow=None
    else:
      self._tooLow = int(tooLow)

    if (tooHigh is None) or tooHigh=="":
      self._tooHigh = None
    else:
      self._tooHigh = int(tooHigh)
      
    if (min_val is None) or min_val == "":
        self._min = float("-inf")
    else:
        self._min = float(min_val)
        
    if (max_val is None) or max_val == "":
        self._max = float("inf")
    else:
        self._max = float(max_val)
     

  def __repr__(self):
    formula = escape(str(self._formula))
    usesPart = self._buildStringPart("uses", self._uses)
    tooLowPart = self._buildStringPart("tooLow", self._tooLow)
    tooHighPart = self._buildStringPart("tooHigh", self._tooHigh)
    type_part = ' type="%s"' % self.resulttype
    
    if self._min == float("-inf"):
        min_part = ""
    else:
        min_part = " min=\"%s\" " % self._min
        
    if self._max == float("inf"):
        max_part = ""
    else:
        max_part = " max=\"%s\" " % self._max
    
    name=self._name
    
    return """<heuristic name="%s" formula="%s"%s%s%s%s%s%s />""" % (name,
                                                                    formula,
                                                                    usesPart,
                                                                    tooLowPart,
                                                                    tooHighPart,
                                                                    min_part,
                                                                    max_part,
                                                                    type_part)
  
  def __eq__(self, other):
      if self._name != other._name:
          return False
          
      if repr(self._formula) != repr(other._formula):
          return False
          
      #TODO: is there any need to actually check all the other fields?
      
      return True
      
      
  def __ne__(self, other):
      return not self.__eq__(other)
      
  @staticmethod
  def generate(name, available_features, resulttype, min_val, max_val):
      newformula = formula.generate(available_features, resulttype, min_val, 
                                    max_val)
      return Heuristic(name, str(newformula), resulttype, min_val=min_val, 
                       max_val=max_val)
  
  
  def _buildStringPart(self, varName, variable):
    if variable is not None:
      return ' %s="%s"' % (varName, variable)
    else:
      return ""

  @property
  def name(self):
    return self._name

  @property
  def formula(self):
      return self._formula
  
  @property
  def uses(self):
    return self._uses

  @property
  def tooLow(self):
    return self._tooLow

  @property
  def tooHigh(self):
    return self._tooHigh
    
  @property
  def min_val(self):
      return self._min
      

  @property
  def max_val(self):
      return self._max

  def evolve(self, available_features):
    formulaObj = maximaparser.parse(self._formula)
    formulaObj.set_available_features(available_features)
    formulaObj.evolve(self._min, self._max)
    self._formula=str(formulaObj)

  def derive_needed_heuristic(self, available_features):
      """Return a NeededHeuristic object corresponding to the current heuristic.

The returned object will have the name, min and max fields set to the same 
values as the heuristic object it is invoked upon.
Everything else will be None"""
      return NeededHeuristic(self._name, available_features, self.resulttype, 
                             min_val=self._min, max_val=self._max)
      
  



class AvailableFeatures(dict):
    def importFromXmlDOM(self, xmlDOM):
        for heuristic_dom in xmlDOM.getElementsByTagName("availablefeatures"):
            heuristic_name = heuristic_dom.getAttribute("heuristic_name")
            feature_list = self._import_feature_names(heuristic_dom)
            self[heuristic_name] = feature_list

    def importFromXml(self, xmlFileName):
        self.importFromXmlDOM(xml.dom.minidom.parse(xmlFileName))


    def _import_feature_names(self, heuristic_dom):
        feature_list = []
        for feature in heuristic_dom.getElementsByTagName("feature"):
            feature_name = feature.getAttribute("name")
            feature_list.append(feature_name)
        return feature_list


class HeuristicSet(dict):
  """Represents a set of heuristics"""
  def __setitem__(self, key, value):
    if not isinstance(value, Heuristic):
      raise TypeError
    super(HeuristicSet, self).__setitem__(key, value)

  def toXmlStrings(self):
    return [str(self[name]) for name in self]

  def toXmlFile(self, filename):
    outfile = open(filename, "w")
    outfile.write("<set>\n")
    for xmlstring in self.toXmlStrings():
      outfile.write("\t")
      outfile.write(xmlstring)
      outfile.write("\n")
    outfile.write("</set>\n")
    outfile.close()

  def importFromXmlString(self, xmlString):
    self.importFromXmlDOM(xml.dom.minidom.parseString(xmlString))

  def importFromXml(self, xmlFileName):
    self.importFromXmlDOM(xml.dom.minidom.parse(xmlFileName))

  def importFromXmlDOM(self, xmlDOM):
    for heuristicXML in xmlDOM.getElementsByTagName("heuristic"):
      name = heuristicXML.getAttribute("name")
      formulastr = heuristicXML.getAttribute("formula")
      uses = heuristicXML.getAttribute("uses")
      tooLow = heuristicXML.getAttribute("tooLow")
      tooHigh = heuristicXML.getAttribute("tooHigh")
      minVal = heuristicXML.getAttribute("min")
      maxVal = heuristicXML.getAttribute("max")
      resulttype_str = heuristicXML.getAttribute("type")
      resulttype = formula.resulttype(resulttype_str)

      #Use the parser to validate (and to constant fold) the formula
      formulastr = str(maximaparser.parse(formulastr))
      self[name] = Heuristic(name, formulastr, resulttype, uses, tooLow, 
                             tooHigh, minVal, maxVal)

  def complete(self, neededHeuristics, db, N):
    """Complete the sets using the given db, so that it contains all the
heuristics specified in the heuristicNames list.

Every missing heuristic is completed with one randomly taken from the best N
heuristics in the database  """
    #Find the missing heuristics
    missingHeuristics = [heur for heur in neededHeuristics 
                         if heur.name not in self]

    #Complete the set
    for missing_heur in missingHeuristics:
      logger.debug("----------------------")
      logger.debug("Heuristic %s is missing", missing_heur)
      bestN = db.getBestNHeuristics(missing_heur.name, N)
      if len(bestN) == 0:
          #No such heuristic in the DB. Do not complete the set
          #This is not a problem. It's probably a new heuristic:
          #just ignore it and it will fall back on the default implemented
          #into the compiler
          logger.debug("Not in the DB. Generate random heuristic:")
          heur = Heuristic.generate(missing_heur.name, 
                                    missing_heur.available_features,
                                    missing_heur.resulttype,
                                    missing_heur.min_val, 
                                    missing_heur.max_val)
          logger.debug(str(heur))
      else:  
          selected_formula = advancedrandom.random_roulette_selection(bestN)
          heur = missing_heur.derive_heuristic(selected_formula)
      
          if random.random() < CONF_EXPLORATION_PROBABILITY:
              #Generate a new formula by modifying the existing one        
              heur.evolve(missing_heur.available_features)
              logger.debug("Evolution\nFrom: %s\nTo: %s", selected_formula, heur.formula)
          else:
              logger.debug("No evolution for: %s", selected_formula)
            
      logger.debug("----------------------")
      self[heur.name] = heur
      

  def forceEvolution(self, all_available_features):
    (name, heuristic) = random.choice(self.items())
    assert len(all_available_features[name])  > 0
    heuristic.evolve(all_available_features[name])


  def ensureUnique(self, hSetCollection, all_available_features):
    """Ensure that the current heuristic set is unique with respect to those in
the given collection.

If an identical heuristic set is found in the collection, the current one
is evolved until it becomes different and unique"""
    
    while self in hSetCollection:
        #Prevent having two identical sets of heuristics
        logger.info("hSet is equal to one already in the collection. Evolve it")
        pp = pprint.PrettyPrinter()
        logger.debug("Old: %s", pp.pformat(self))
        self.forceEvolution(all_available_features)
        logger.debug("New (evolved): %s", pp.pformat(self))



class HeuristicManager:
  """Manages sets of heuristics stored in a file with the following format:
<heuristics>
  <set>
    <heuristic name="heuristicName" formula="a+b+c" />
    <heuristic name="heuristicName2" formula="a+b+d" />
  </set>
  <set>
    <heuristic name="heuristicName3" formula="x+y*z" />
    <heuristic name="heuristicName4" formula="a+g+s" />
  </set>
</heuristics>
"""
  def __init__(self, heuristicSetFileName = None):
    self._heuristicSets = []
    self._loadHeuristicsFromFile(heuristicSetFileName)
    self.resetToDefaultFromFile()


  def _loadHeuristicsFromFile(self, heuristicSetFileName):
    """Load the heuristics from the specified file
If the name is None, nothing is loaded"""
    self._heuristicSetsInFile = []

    if heuristicSetFileName is None:
      return

    self._xml = xml.dom.minidom.parse(heuristicSetFileName)

    # Extract information
    for hSet in self._xml.getElementsByTagName("set"):
      self._heuristicSetsInFile.append(self._parseHeuristicSet(hSet))


  def resetToDefaultFromFile(self):
    """Reset the set of heuristics to the one contained in the file
specified at the construction of the HeuristicManager.
Removes every other heuristic"""
    self._heuristicSets = copy.deepcopy(self._heuristicSetsInFile)

  def _parseHeuristicSet(self, hSetXML):
    "Parses a xml heuristic set returning it as a list of pairs name-formula"
    hSet = HeuristicSet()
    hSet.importFromXmlDOM(hSetXML)
    return hSet

  def heuristicSet(self, i):
    """Get the i-th heuristic set"""
    return self._heuristicSets[i]

  def allHeuristicSets(self):
    return self._heuristicSets


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
               knowledge=None):
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
            self._db.markAsUsed(h_set, uses=1)


        count = count +1

  def _generateHSetsByElitism(self, neededHeuristics, eliteSize, 
                              get_n_heuristics):
    """Generate "eliteSize" heuristic sets by elitism, that is by
getting the current best heuristics, without modifying them"""

    allHSets = []
    #Get the best N heuristics of each kind
    #TODO: use information about the best heuristic sets!!!
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

    elite = self._generateHSetsByElitism(neededHeuristics, NUM_ELITE_BEST, 
                                         self._db.getBestNHeuristics)
    allHSets.extend(elite)
    elite = self._generateHSetsByElitism(neededHeuristics, 
                                         NUM_ELITE_MOST_FREQUENT, 
                                         self._db.getNMostFrequentHeuristics)
    allHSets.extend(elite)
    numGenerated = len(allHSets)

    #Generate the ramaining needed (empty) heuristicSets
    numNeeded = self._minTrialNumber - numGenerated
    for _ in range(numNeeded):
      allHSets.append(HeuristicSet())

    #Complete heuristic sets
    count=0
    for hSet in allHSets:
      logger.debug("Completing %s", hSet)
      hSet.complete(neededHeuristics, self._db, CONF_PICK_BEST_N)

      previousHSets = allHSets[:count]
      hSet.ensureUnique(previousHSets, self._get_available_features(benchmark))

      count = count + 1

    if self.use_mapreduce:
        self._test_with_mapreduce(benchmark, allHSets, additionalParameters)
    else:
        self._test_sequentially(benchmark, allHSets, additionalParameters)


  def use_learning(self, benchmark, learn=True):
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
