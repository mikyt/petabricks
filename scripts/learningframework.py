"""Framework implementing long term learning of heuristics """
import random
import xml.dom.minidom
import maximaparser
import heuristicdb
import os
import copy
import pprint
import random
from xml.sax.saxutils import escape


#---------------- Config ------------------
CONF_MIN_TRIAL_NUMBER = 6
CONF_EXPLORATION_PROBABILITY = 0.7
CONF_PICK_BEST_N = 5
#------------------------------------------

class AllCandidatesCrashError(Exception):
  pass

class Candidate:
  """Represents a learning candidate. Objects can be considered candidate 
if they have this set of attributes.
They do NOT need to inherit from this class"""
  def __init__(self, heuristicSet, failed, assignScores, originalIndex):
    if heuristicSet is None:
      self.heuristicSet = HeuristicSet()
    else:
      self.heuristicSet = heuristicSet
    
    self.failed = failed
    self.assignScores = assignScores
    self.originalIndex = originalIndex
    
class FailedCandidate(Candidate):
  """Represents a candidate that failed during compilation or tuning.
If assignScores is False, when this candidate is graded it's only marked as used
but not given any point (thus it is penalized)"""
  def __init__(self, heuristicSet = None, assignScores = True):
    Candidate.__init__(self, heuristicSet, failed=True, assignScores=assignScores, originalIndex=None)
    if heuristicSet is None:
      self.heuristicSet = HeuristicSet()
    else:
      self.heuristicSet = heuristicSet


class SuccessfulCandidate(Candidate):
  """Represents a candidate that was executed correctly"""
  def __init__(self, heuristicSet):
    Candidate.__init__(self, heuristicSet, failed=False, assignScores=True, originalIndex=None)

  
class HeuristicSet(dict):
  """Represents a set of heuristics"""
  
  def toXmlStrings(self):
    return ["<heuristic name=\""+name+"\" formula=\""+escape(self[name])+"\" />" for name in self]
  
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
      formula = heuristicXML.getAttribute("formula")
      #Use the parser to validate (and to constant fold) the formula
      formula = str(maximaparser.parse(formula))
      self[name] = formula
  
  def complete(self, heuristicNames, db, N):
    """Complete the sets using the given db, so that it contains all the 
heuristics specified in the heuristicNames list.

Every missing heuristic is completed with one randomly taken from the best N 
heuristics in the database  """
    #Find the missing heuristics
    missingHeuristics = list(heuristicNames)
    for name in self:
      try:
        missingHeuristics.remove(name)
      except ValueError:
        #A heuristic could be in the input file, but useless, therefore not in
        #the missingHeuristic list
        pass
      
    #Complete the set
    for heuristic in missingHeuristics:
      print "----------------------"
      print "Heuristic %s is missing" % heuristic
      bestN = db.getBestNHeuristics(heuristic, N)
      if len(bestN) == 0:
        #No such heuristic in the DB. Do not complete the set
        #This is not a problem. It's probably a new heuristic:
        #just ignore it and it will fall back on the default implemented 
        #into the compiler
        print "Not in the DB. Fall back on default"
        print "----------------------"
        #raw_input()
        continue
      formula = random.choice(bestN)
      
      if random.random() < CONF_EXPLORATION_PROBABILITY:
        #Generate a new formula by modifying the existing one
        formulaObj = maximaparser.parse(formula)
        formulaObj.evolve()
        
        print "EVOLUTION!"
        print "From: " + formula
        print "To: " + str(formulaObj)
        formula = str(formulaObj)
      else:
	print "No mutation for "+formula
      print "----------------------"
      self[heuristic] = formula
      #raw_input()

    return False
    
  def forceEvolution(self):
    (name, formula) = random.choice(self.items())
    formulaObj = maximaparser.parse(formula)
    formulaObj.evolve()
    self[name]=str(formulaObj)
    
    
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
      
    print "Original heuristic set from file: %s" % self._heuristicSetsInFile
    
    
  def resetToDefaultFromFile(self):
    """Reset the set of heuristics to the one contained in the file
specified at the construction of the HeuristicManager.
Removes every other heuristic"""
    print "Resetting the heuristic sets"
    print "They were: %s" % self._heuristicSets
    self._heuristicSets = copy.deepcopy(self._heuristicSetsInFile)
    print "Now they are: %s" % self._heuristicSets
    
  def _parseHeuristicSet(self, hSetXML):
    """Parses a xml heuristic set returning it as a list of pairs name-formula"""
    hSet = HeuristicSet()
    hSet.importFromXmlDOM(hSetXML)
    return hSet
     
  def heuristicSet(self, i):
    """Get the i-th heuristic set"""
    return self._heuristicSets[i]
  
  def allHeuristicSets(self):
    return self._heuristicSets
    
  def reset(self):
    """Restore the heuristic sets to those contained in the input file"""




class CandidateList(list):  
  def __init__(self, sortingKey):
    self._sortingKey = sortingKey
    
  def addOriginalIndex(self):
    count = 0
    for candidate in self:
      candidate.originalIndex = count
      count = count + 1
      
  def sort(self):
    #Call sort() of "list"
    super(CandidateList, self).sort(key = self._sortingKey)
        
    
  
    


class Learner:
  def __init__(self, 
               testHSet, 
               candidateSortingKey,
               heuristicSetFileName = None, 
               setup = None, 
               tearDown = None,
               getNeededHeuristics = None):
    self._heuristicManager = HeuristicManager(heuristicSetFileName)
    self._minTrialNumber = CONF_MIN_TRIAL_NUMBER
    self._db = heuristicdb.HeuristicDB()
    self._setup = setup
    self._testHSet = testHSet
    self._candidateSortingKey = candidateSortingKey
    self._tearDown = tearDown
    
    if getNeededHeuristics is None:
      #Return an empty list
      self._getNeededHeuristics = lambda : []
    else:
      self._getNeededHeuristics = getNeededHeuristics
      
    random.seed()
    
  
  def storeCandidatesDataInDB(self, candidates):
    """Store data from all the info file, with score.
The candidates should already be ordered (from the best to the worst) and 
with the originalIndex field added"""
    numCandidates = len(candidates)
    count = 0
    for candidate in candidates:
      print "Storing this heuristic set:"
      pp=pprint.PrettyPrinter()
      pp.pprint(candidate.heuristicSet)
      #raw_input()
      score = (numCandidates - count) / float(numCandidates)
      self._db.markAsUsed(candidate.heuristicSet)
      
      if candidate.assignScores:
        self._db.increaseScore(candidate.heuristicSet, score)
        
      count = count +1
      
    
  def _generateAndTestHSets(self, benchmark, additionalParameters):
    candidates = additionalParameters["candidates"]
    neededHeuristics = additionalParameters["neededHeuristics"]
    
    #Get the initial heuristic sets
    self._heuristicManager.resetToDefaultFromFile()
    allHSets = self._heuristicManager.allHeuristicSets()
    
    while len(allHSets) < (self._minTrialNumber): #Not enough hSets!
      allHSets.append(HeuristicSet())
    
    #Complete heuristic sets
    count = 0
    for hSet in allHSets:
      print "Completing %s" % hSet
      hSet.complete(neededHeuristics, self._db, CONF_PICK_BEST_N)
      
      while hSet in allHSets[:count]:
	#Prevent having two identical sets of heuristics
	print "hSet %d is equal to the current one is already present in the list" % count
	print "HSet:"
	pp=pprint.PrettyPrinter()
	pp.pprint(hSet)
	print "List:"
	pp.pprint(allHSets[:count])
	
	hSet.forceEvolution()
	
	print "hSet %d has been evolved to: " % count
	pp.pprint(hSet)
	#raw_input()
	
      count = count + 1
    
    count = 0
    for hSet in allHSets:
      count = count + 1
      currentCandidate = self._testHSet(benchmark, count, hSet, additionalParameters) 
      candidates.append(currentCandidate)
    
    if candidates[0].failed:
      raise AllCandidatesCrashError
    
    
    
  def learnHeuristics(self, benchmark):
    print "Learning: %s" % benchmark
    
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
    print "Needed heuristics: %s" % neededHeuristics
    
    canLearn = (len(neededHeuristics) > 0)
    if canLearn:
      self._generateAndTestHSets(benchmark, additionalParameters)
      
    candidates.addOriginalIndex()
    candidates.sort()
    
    if canLearn:
      self.storeCandidatesDataInDB(candidates)
    
    
    if self._tearDown is not None:
      self._tearDown(benchmark, additionalParameters)
    
    return 0
    
