import logging
import random

logger = logging.getLogger(__name__)

_randomMIN = -100
_randomMAX = 100
_mutationProbability = 0.3

class Error(Exception):
    """Base class for all the exceptions of this module"""
    pass


class NoElementException(Error):
    pass    


class NoFeatureAvailable(Error):
    pass

def random_roulette_selection(weighted_candidates):
    """Perform roulette selection between the given candidates.
weighted_candidates is a list of pairs (weight, candidate).

The higher the weight, the higher the probability of being chosen"""
    total_weight = sum(candidate[0] for candidate in weighted_candidates)
    
    winner = random.uniform(0,1) * total_weight
    
    weight_sum = 0
    for candidate in weighted_candidates:
        weight = candidate[0]
        new_weight_sum = weight_sum + weight
        if weight_sum <= winner and winner < new_weight_sum:
            winner_content = candidate[1]
            return winner_content
        weight_sum = new_weight_sum
    
    #If we are here, winner=1
    #We have to return the last candidate
    num_candidates = len(weighted_candidates)
    last_candidate = weighted_candidates[num_candidates-1] 
    return last_candidate[1]
            
        
    

def random_int(min_val, max_val):
    """Limited randomizer"""
    if min_val == float("-inf"):
        #min_val = -sys.maxint
        min_val = _randomMIN
    if max_val == float("inf"):
        #max_val = sys.maxint
        max_val = _randomMAX
    return random.randint(min_val, max_val) 
    
    
def random_float(min_val, max_val):
    """Limited randomizer"""
    if min_val == float("-inf"):
        #min_val = -sys.maxint
        min_val = _randomMIN
    if max_val == float("inf"):
        #max_val = sys.maxint
        max_val = _randomMAX
    return random.uniform(min_val, max_val)
    
 
def selectDifferentElement(element, theList):
  """Select an element from the list, different from the given one"""
  if len(theList) == 1 and element==theList[0]:
    raise NoElementException()
  
  newElement = random.choice(theList)
  while newElement == element:
    newElement = random.choice(theList)
    
  return newElement


def isImmediateNumber(formula):
  return isinstance(formula, FormulaInteger) or \
         isinstance(formula, FormulaFloat)

def outside_limits(value, min_val, max_val):
    if value < min_val or value > max_val:
        return True
    return False
    
def evolution_coefficient(value, min_val, max_val):
    """Determine the evolution coefficient.
    
It's a number comprised between -1 and 1.
If the current value is already equal to min (respectively max)
the coefficient will be strictly positive (respectively negative)"""
    if value == min_val:
        return random.uniform(0, 1)
        
    if value == max_val:
        return random.uniform(-1, 0)
        
    return random.uniform(-1, 1)
    

def generate(available_features, min_val=float("-inf"), max_val=float("inf")):
    """Generates a completely random formula, acknowledging the limits,
if given"""

    formula_types = [(3.5, FormulaVariable), 
                     (3.5, FormulaInteger),
                     (2, FormulaBinop),
                     (1, FormulaIf)]
                     
    #TODO FormulaBool and FormulaFloat are not in formula_types, because in
    #order to be used a way to specify the type of the formula should be 
    #available
    Formula = random_roulette_selection(formula_types) 
    generatedformula = Formula.generate(available_features, min_val, max_val)
    return FormulaContainer(generatedformula)


    
class FormulaContainer:
    """This wrapper class allows to completely mutate formulas through 
generation of new formulas or subformulas.

When mutation through generation of a new formula is required for a top-level
formula, it is performed by this wrapper.
Re-generation of subformulas (such as in "if" constructs or binary operations)
is performed by the "mutate" method of the construct itself."""
    def __init__(self, formulaobj):
        self._formulaobj = formulaobj
        
    def __repr__(self):
        return repr(self._formulaobj)
        
    def evolve(self, min_val=float("-inf"), max_val=float("inf")):
        if random.random() < _mutationProbability:
            #Generate a completely new formula
            available_features = self.get_available_features()
            self._formulaobj = generate(available_features, min_val, max_val)
            return 
        return self._formulaobj.evolve(min_val, max_val)
        
    def set_available_features(self, available_features):
        assert available_features is not None
        self._formulaobj.set_available_features(available_features)
    
    def get_available_features(self):
      return self._formulaobj.get_available_features()
      
    #The generate method need not be implemented: 
    #this is just a wrapper class!
    
    
        

class FormulaVariable:
  def __init__(self, ident):
    self.ident=ident
    self._available_features = None
    
  def __repr__(self):
    return self.ident
    
  def evolve(self, _=None, __=None):
    #No values to mutate in a variable
    return False
  
  def set_available_features(self, available_features):
      self._available_features = available_features
  
  def get_available_features(self):
      return self._available_features
      
  @staticmethod
  def generate(available_features, unused_min_val=None, unused_max_val=None):
      if not available_features:
          raise NoFeatureAvailable
      
      name = random.choice(available_features)
      newformula = FormulaVariable(name)
      newformula.set_available_features(available_features)
      return newformula
      
  
class FormulaInteger:
  def __init__(self, value):
    self.value=value
    self._available_features = None
    
  def __repr__(self):
    return str(self.value)
    
  def evolve(self, min_val=float("-inf"), max_val=float("inf")):
    if random.random() < _mutationProbability:
        return self.mutateValue(min_val, max_val)
    
    #Evolve (=increment/decrement of at most 100% of the original value)
    oldValue = self.value 
    self.value = int(self.value + (self.value * 
                                   evolution_coefficient(self.value,
                                                         min_val,
                                                         max_val)))
    if oldValue == self.value:
      #The value did not change. It was too small to be modified that way
      #Force a change
      if random.random() < 0.5:
        self.value = self.value - 1
      else:
        self.value = self.value + 1
        
    if outside_limits(self.value, min_val, max_val):
        #Looks like the limits are really tight
        #Pick a random value in between
        return self.mutateValue(min_val, max_val)
        
    return True

  def mutateValue(self, min_val, max_val):
    """Get a completely random new value"""
    if min_val==max_val:
        self.value = min_val
        return False
        
    oldValue = self.value 
    while oldValue == self.value:
        self.value = random_int(min_val, max_val)
    return True
    
  def set_available_features(self, available_features):
      self._available_features = available_features
      
  def get_available_features(self):
      return self._available_features
      
  @staticmethod
  def generate(available_features, min_val, max_val):
      newformula = FormulaInteger(0)
      newformula.mutateValue(min_val, max_val)
      newformula.set_available_features(available_features)
      return newformula
       

class FormulaBool:
  def __init__(self, value):
    self.value=value
    self._available_features = None
    
  def __repr__(self):
    if self.value:
      return "true"
    else:
      return "false"
      
  def evolve(self, unused_min_val=None, unused_max_val=None):
    if random.random() < 0.5:
      self.value = False
    else:
      self.value = True
    return True  
    
  def set_available_features(self, available_features):
      self._available_features = available_features
  
  def get_available_features(self):
      return self._available_features
      
  @staticmethod
  def generate(available_features, unused_min_val=None, unused_max_val=None):
      newformula = FormulaBool(True)
      newformula.evolve()
      newformula.set_available_features(available_features)
      return newformula
      
      
class FormulaFloat:
  def __init__(self, value):
    self.value=value
    self._available_features = None
    
  def __repr__(self):
    return str(self.value)
    
  def evolve(self, min_val=float("-inf"), max_val=float("inf")):
    if random.random() < _mutationProbability:
      return self.mutateValue(min_val, max_val)
      
    #Evolve (=increment/decrement of at most 100% of the original value)
    oldValue = self.value 
    self.value = self.value + (self.value * evolution_coefficient(self.value,
                                                                  min_val,
                                                                  max_val))
    if oldValue == self.value:
      #The value did not change. It was too small to be modified that way
      #Force a change
      if random.random() < 0.5:
        self.value = self.value - 1
      else:
        self.value = self.value + 1
        
    if outside_limits(self.value, min_val, max_val):
        #Looks like the limits are really tight
        #Pick a random value in between
        return self.mutateValue(min_val, max_val)
    
    return True
    
    
  def mutateValue(self, min_val, max_val):
      """Get a completely random new value"""
      if min_val==max_val:
          self.value = min_val
          return False
        
      oldValue = self.value
      while(oldValue==self.value):
        self.value = random_float(min_val, max_val)
      return True
      
  def set_available_features(self, available_features):
      self._available_features = available_features
  
  def get_available_features(self):
      return self._available_features
      
  @staticmethod
  def generate(available_features, min_val, max_val):
      newformula = FormulaFloat(0)
      newformula.mutateValue(min_val, max_val)
      newformula.set_available_features(available_features)
      return newformula
 
  
  
  
    
class FormulaBinop:
  comparison_operators=["=", "#", "<", ">", ">=", "<="]
  binary_logic_operators=["and", "or"]
  arithmetic_operators=["+", "-", "*", "/"]
  all_operators = list(comparison_operators)
  all_operators.extend(binary_logic_operators)
  all_operators.extend(arithmetic_operators)
                        
                    
  def __init__(self, op, left, right):
    self.op=op
    self.left=left
    self.right=right
    self._available_features = None
    
  def __repr__(self):
    reprStr = "("+ str(self.left) +" "+ str(self.op) + " " + str(self.right)+")"
    if not (isImmediateNumber(self.left) and isImmediateNumber(self.right)):
      #Return extended representation
      return reprStr
    else:
      #Constant folding
      #Handle special cases where sintax is different
      op = self._pythonOperator()
      reprStr = "("+ str(self.left) +" "+ str(op) + " " + str(self.right)+")"
      
      return str(eval(reprStr))
  
  def _pythonOperator(self):
    """Return the python representation of the operator"""
    if self.op == "=":
      return "=="
    elif self.op == "#":
      return "!="
    else:
      return self.op
    
  def evolveValue(self):
    """Randomly mutates one of the values (int, float, bool) that are in the 
formula.
If no value is present, nothing is changed.

The formula is mutated in place.

Returns true if the formula was actually mutated, false otherwise"""
    mutated = False
    if random.random() < 0.5:
      mutated = self.left.evolve()
      if not mutated:
        mutated = self.right.evolve()
    else:
      mutated = self.right.evolve()
      if not mutated:
        mutated = self.left.evolve()
    
    return mutated
  
  
  def evolveOperator(self):
   
    try:
      if self.op in self.comparison_operators:
        self.op = selectDifferentElement(self.op, self.comparison_operators)
      elif self.op in self.binary_logic_operators:
        self.op = selectDifferentElement(self.op, self.binary_logic_operators)
      elif self.op in self.arithmetic_operators:
        self.op = selectDifferentElement(self.op, self.arithmetic_operators)
      else:
        raise Exception("Unknown operator: " + self.op)
    except NoElementException:
      return False
       
    return True

    
  def mutate(self, min_val, max_val):
      newsubformula = generate(self._available_features, min_val, max_val)
      if random.random() < 0.5:
          self.left = newsubformula
      else:
          self.right = newsubformula
      return True
      

  def evolve(self, min_val=float("-inf"), max_val=float("inf")):
    """Randomly mutate one of the values or the binary operation, or the 
operator"""
    if random.random() < _mutationProbability:
        self.mutate(min_val, max_val)
        
    choices=range(2)
    random.shuffle(choices)
    for choice in choices:
      mutated=False
      #TODO: change evolution algorithm (using a simbolic framework like sympy?) 
      #to actually acknowledge min_val and max_val
      if choice==0:
        mutated=self.evolveValue()
      elif choice==1:
        mutated=self.evolveOperator()
      
      if mutated:
        return True
    
    return False
    
  def set_available_features(self, available_features):
      self._available_features = available_features
      
      self.left.set_available_features(available_features)
      self.right.set_available_features(available_features)
  
  def get_available_features(self):
      return self._available_features
      
  @classmethod
  def generate(cls, available_features, min_val, max_val):
      op = random.choice(cls.all_operators)
      newformula = FormulaBinop(op, 
                                generate(available_features, 
                                         min_val, 
                                         max_val), 
                                generate(available_features, 
                                         min_val, 
                                         max_val))
      newformula.set_available_features(available_features)
      return newformula
      
      
      
class FormulaIf:
  def __init__(self, cond, thenClause, elseClause=None):
    self.cond = cond
    self.thenClause = thenClause
    self.elseClause = elseClause
    self._available_features = None
    
  def __repr__(self):
    if self.elseClause is not None:
      elsePart=" else " + str(self.elseClause)
    else:
      elsePart=""
      
    return "if " + str(self.cond) + " then " + str(self.thenClause) + elsePart
  
  
  def mutate(self, min_val, max_val):
      newsubformula = generate(self._available_features, min_val, max_val)
      choice = random.randrange(3)
      if choice == 0:
          self.cond = newsubformula
      elif choice == 1:
          self.thenClause = newsubformula
      else:
          self.elseClause = newsubformula
          
          
  def evolve(self, min_val=float("-inf"), max_val=float("inf")):
    if random.random() < _mutationProbability:
        self.mutate(min_val, max_val)
        
    choices = range(3)
    random.shuffle(choices)
    for choice in choices:
      mutated = False
      if choice==0:
        mutated = self.cond.evolve()
      elif choice==1:
        mutated = self.thenClause.evolve(min_val, max_val)
      elif choice==2 and self.elseClause is not None:
        mutated = self.elseClause.evolve(min_val, max_val)
      
      if mutated:
        return True
    
    return False

  def set_available_features(self, available_features):
      self._available_features = available_features
      
      self.cond.set_available_features(available_features)
      self.thenClause.set_available_features(available_features)
      self.elseClause.set_available_features(available_features)
  
  def get_available_features(self):
      return self._available_features
      
  @staticmethod
  def generate(available_features, min_val, max_val):
      newformula = FormulaIf(generate(available_features, 
                                      min_val, 
                                      max_val), 
                             generate(available_features,
                                      min_val,
                                      max_val), 
                             generate(available_features,
                                      min_val,
                                      max_val))
      newformula.set_available_features(available_features)
      return newformula