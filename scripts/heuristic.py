import advancedrandom
import formula
import logging
import maximaparser
import random
import pprint
import copy
import xml.dom.minidom

from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

#-------------- Config --------------
CONF_EXPLORATION_PROBABILITY = 0.2
CONF_MAX_EVOLUTION_RATE = 0.3
#------------------------------------

resulttype_from_str = formula.resulttype

class Heuristic(object):
  def __init__(self, name, formula, resulttype, uses=None, tooLow=None, tooHigh=None, 
               min_val=None, max_val=None, ID=None, derivesFrom=None, score=None):
    self._name = name
    self._formula = formula
    self.ID = ID
    self.derivesFrom = derivesFrom
    self.score = score
    
    self.resulttype = resulttype_from_str(resulttype)

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
    ID_part = self._buildStringPart("ID", self.ID)
    derivesFrom_part = self._buildStringPart("derivesFrom", self.derivesFrom)
    
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
    
    return """<heuristic name="%s" formula="%s"%s%s%s%s%s%s%s%s />""" % (name,
                                                            formula,
                                                            usesPart,
                                                            tooLowPart,
                                                            tooHighPart,
                                                            min_part,
                                                            max_part,
                                                            type_part,
                                                            ID_part,
                                                            derivesFrom_part)
  
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
                       max_val=max_val, ID=-1)
  
  
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

  def increase_uses(self, uses=1):
      self._uses = self._uses + uses
      
  @property
  def tooLow(self):
    return self._tooLow

  def increase_tooLow(self, count=1):
      self._tooLow = self._tooLow + count
  
  @property
  def tooHigh(self):
    return self._tooHigh
  
  def increase_tooHigh(self, count=1):
      self._tooHigh = self._tooHigh + count
  
  @property
  def min_val(self):
      return self._min
      

  @property
  def max_val(self):
      return self._max

      
  def evolve(self, available_features):
    assert self.ID
    
    formulaObj = maximaparser.parse(self._formula)
    formulaObj.set_available_features(available_features)
    formulaObj.evolve(self._min, self._max)
    newformula = str(formulaObj)
    logger.debug("Heuristic %s evolved", self.name)
    logger.debug("from: %s", self.formula)
    logger.debug("to:   %s", newformula)
    self._formula = newformula

    if self.ID != -1:
        self.derivesFrom = self.ID 
            
    self.ID = -1
    
  def derive_needed_heuristic(self, available_features):
      """Return a NeededHeuristic object corresponding to the current heuristic.

The returned object will have the name, min and max fields set to the same 
values as the heuristic object it is invoked upon.
Everything else will be None"""
      return NeededHeuristic(self._name, available_features, self.resulttype, 
                             min_val=self._min, max_val=self._max)
      
  def evaluate(self, valuemap):
      """Evaluate the current heuristic with the values contained in the map
      (name : value)"""
      formulaObj = maximaparser.parse(str(self._formula))
      pstring = formulaObj.to_python_string()
      res = eval(pstring, valuemap)
      del valuemap['__builtins__'] #Added by eval
     
      return res
      
  def prepare_for_usage_statistics(self):
      self._uses = 0
      self._tooLow = 0
      self._tooHigh = 0
      
class FeatureValueMap(dict):
    def importFromXmlDOM(self, xmlDOM):
        for feature_dom in xmlDOM.getElementsByTagName("feature"):
            feature_name = feature_dom.getAttribute("name")
            feature_value = float(feature_dom.getAttribute("value"))
            
            self[feature_name] = feature_value
           
           
    def importFromXml(self, xmlFileName):
        self.importFromXmlDOM(xml.dom.minidom.parse(xmlFileName))

        
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

  def __repr__(self):
      return self.toXmlString()

  def toXmlStringList(self):
    return [str(self[name]) for name in self]

  def toXmlString(self):
       outlist = []
       outlist.append("<set>")
       outlist.extend(["\t"+ s for s in self.toXmlStringList()])
       outlist.append("</set>\n")
       return "\n".join(outlist)
    
  def toXmlFile(self, filename):
    outfile = open(filename, "w")
    outfile.write(self.toXmlString())
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
          logger.debug("Not in the DB. Generate random heuristic:")
          heur = Heuristic.generate(missing_heur.name, 
                                    missing_heur.available_features,
                                    missing_heur.resulttype,
                                    missing_heur.min_val, 
                                    missing_heur.max_val)
          logger.debug(str(heur))
      else:  
          for_roulette = [(heur.score, heur) for heur in bestN]
          selected_heur = advancedrandom.random_roulette_selection(for_roulette)
          heur = missing_heur.derive_heuristic(selected_heur.formula, selected_heur.ID)
            
      self[heur.name] = heur
      

  def evolve(self, all_available_features):
      if random.random() < CONF_EXPLORATION_PROBABILITY:
          evolution_rate = random.uniform(0, CONF_MAX_EVOLUTION_RATE)
          tobechanged = max(1, int(len(self)*evolution_rate)) #At least one!
          for _ in range(tobechanged):
              self.forceEvolution(all_available_features)
          
  def forceEvolution(self, all_available_features):
    (name, heuristic) = random.choice(self.items())
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

  
  def provide_formulas(self, neededHeuristics):
      """Return an heuristic set made by all the elements of neededHeuristics
      that could find a corresponding formula in the current heuristic set.
      The other data of each heuristic (min, max, etc) are taken from 
      neededHeuristics."""
      new_hset = HeuristicSet()
      for neededHeuristic in neededHeuristics:
          name = neededHeuristic.name
          try:
              formula = self[name].formula
              ID = self[name].ID
              new_hset[name] = neededHeuristic.derive_heuristic(formula, ID)
          except KeyError:
              #No such heuristic in the current hset
              #Just exclude the heuristic from the new hset
              pass
      return new_hset
          
          
  def prepare_for_usage_statistics(self):
      for heuristic in self.itervalues():
          heuristic.prepare_for_usage_statistics()
          
          
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
     
    def derive_heuristic(self, formula, ID):
        return Heuristic(self.name, formula, self.resulttype, 
                         min_val=self.min_val, max_val=self.max_val, ID=ID)
        
