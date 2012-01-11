import logging
import random
import sys

logger = logging.getLogger(__name__)

_mutateMIN = -100
_mutateMAX = 100
_mutationProbability = 0.3

class Error(Exception):
    """Base class for all the exceptions of this module"""
    pass


class NoElementException(Error):
    pass    


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
    

class FormulaVariable:
  def __init__(self, ident):
    self.ident=ident

  def __repr__(self):
    return self.ident
    
  def evolve(self, _=None, __=None):
    #No values to mutate in a variable
    return False
  
  
class FormulaInteger:
  def __init__(self, value):
    self.value=value
    
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
    if min_val == float("-inf"):
        min_val = -sys.maxint
    if max_val == float("inf"):
        max_val = sys.maxint
    while oldValue == self.value:
        self.value = random.randint(min_val, max_val)
    return True


class FormulaBool:
  def __init__(self, value):
    self.value=value
    
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
      
      
class FormulaFloat:
  def __init__(self, value):
    self.value=value
    
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
        self.value = random.uniform(min_val, max_val)
      return True


  
  
  
    
class FormulaBinop:
  def __init__(self, op, left, right):
    self.op=op
    self.left=left
    self.right=right
    
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
    comparison_operators=["=", "#", "<", ">", ">=", "<="]
    binary_logic_operators=["and", "or"]
    arithmetic_operators=["+", "-", "*", "/"]
    
    try:
      if self.op in comparison_operators:
        self.op = selectDifferentElement(self.op, comparison_operators)
      elif self.op in binary_logic_operators:
        self.op = selectDifferentElement(self.op, binary_logic_operators)
      elif self.op in arithmetic_operators:
        self.op = selectDifferentElement(self.op, arithmetic_operators)
      else:
        raise Exception("Unknown operator: " + self.op)
    except NoElementException:
      return False
       
    return True
        
  def evolve(self, unused_min_val=float("-inf"), unused_max_val=float("inf")):
    """Randomly mutate one of the values or the binary operation, or the 
operator"""
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
      
      
class FormulaIf:
  def __init__(self, cond, thenClause, elseClause=None):
    self.cond = cond
    self.thenClause = thenClause
    self.elseClause = elseClause
    
  def __repr__(self):
    if self.elseClause is not None:
      elsePart=" else " + str(self.elseClause)
    else:
      elsePart=""
      
    return "if " + str(self.cond) + " then " + str(self.thenClause) + elsePart
    
  def evolve(self, min_val=float("-inf"), max_val=float("inf")):
    print "START"
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