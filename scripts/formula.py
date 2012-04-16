import logging
import random
from advancedrandom import random_roulette_selection

logger = logging.getLogger(__name__)

_randomMIN = -100
_randomMAX = 100
_mutationProbability = 0.3

#Exception types
class Error(Exception):
    """Base class for all the exceptions of this module"""
    pass

class NoElementException(Error):
    pass    

class NoFeatureAvailable(Error):
    pass

class WrongResultTypeError(Error):
    pass

class ClassStringPrinter(type):
    _class_repr = "ClassStringPrinter"
    
    def __repr__(self):
        return self._class_repr
            
class ResultType(object):
    __metaclass__ = ClassStringPrinter
    pass

#Formula types
class IntegerResult(ResultType):
    _class_repr = "int"
    

class BooleanResult(ResultType):
    _class_repr = "bool"
    

class DoubleResult(ResultType):
    _class_repr = "double"
    

#Functions    
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
    return (isinstance(formula, FormulaInteger) or
            isinstance(formula, FormulaFloat))

def isImmediate(formula):
    return (isinstance(formula, FormulaBool) or
            isImmediateNumber(formula))

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
    

def _specifictype(resulttype):
    if resulttype == BooleanResult:
        return FormulaBool
    elif resulttype == IntegerResult:
        return FormulaInteger
    elif resulttype == DoubleResult:
        return FormulaFloat
    raise WrongResultTypeError


def resulttype(resulttype_str):
    s = str(resulttype_str)
    
    if s == "int":
        return IntegerResult
    elif s == "double":
        return DoubleResult
    elif s == "bool":
        return BooleanResult
    else:
        raise WrongResultTypeError(resulttype_str)    
        
def generate(available_features, resulttype, min_val=float("-inf"), max_val=float("inf")):
    """Generates a completely random formula, acknowledging the limits,
if given"""

    formula_types = [(5, _specifictype(resulttype)),
                     (2, FormulaBinop),
                     (1, FormulaIf)]

    if (len(available_features) > 0) and (resulttype != BooleanResult):
        #TODO: implement support for bool variables
        formula_types.append((4, FormulaVariable))
 
    FormulaT = random_roulette_selection(formula_types) 
    generatedformula = _safe_generate(FormulaT, available_features, resulttype, min_val, max_val)
    return FormulaContainer(generatedformula)
        
        
def _safe_generate(FormulaT, available_features, resulttype, min_val, max_val):
    try:
        gen_formula  = FormulaT.generate(available_features, 
                                        resulttype, 
                                        min_val, 
                                        max_val)
        return gen_formula
    except RuntimeError:
        #If we are here, formula generation exceeded maximum recursion depth
        #Fall back on trivial case
        gen_formula = _specifictype(resulttype).generate(available_features, 
                                                         resulttype, 
                                                         min_val, 
                                                         max_val)
        return gen_formula
                                                  

class Formula(object):
    def set_available_features(self, available_features):
        self._available_features = available_features
  
    def get_available_features(self):
        return self._available_features
      
    def to_python_string(self):
        return str(self)
        

class FormulaContainer(Formula):
    """This wrapper class allows to completely mutate formulas through 
generation of new formulas or subformulas.

When mutation through generation of a new formula is required for a top-level
formula, it is performed by this wrapper.
Re-generation of subformulas (such as in "if" constructs or binary operations)
is performed by the "mutate" method of the construct itself."""
    def __init__(self, formulaobj):
        self._formulaobj = formulaobj
        
    def __repr__(self):
        return str(self._formulaobj)
        
    def evolve(self, min_val=float("-inf"), max_val=float("inf")):
        if random.random() < _mutationProbability:
            #Generate a completely new formula
            available_features = self.get_available_features()
            self._formulaobj = generate(available_features, 
                                        self._formulaobj.resulttype,
                                        min_val, 
                                        max_val)
            return True
        return self._formulaobj.evolve(min_val, max_val)
        
    def set_available_features(self, available_features):
        assert available_features is not None
        self._formulaobj.set_available_features(available_features)
    
    def get_available_features(self):
      return self._formulaobj.get_available_features()
      
    def to_python_string(self):
        return self._formulaobj.to_python_string()
        
    def _set_resulttype(self, resulttype):
        self._formulaobj.resulttype = resulttype
        
    def _get_resulttype(self):
        return self._formulaobj.resulttype
        
    resulttype = property(_get_resulttype, _set_resulttype)
    
    #The generate method need not be implemented: 
    #this is just a wrapper class!
    
    
        

class FormulaVariable(Formula):
  def __init__(self, ident, resulttype=IntegerResult):
    self.ident=ident
    self._available_features = None
    self.resulttype = resulttype
    
  def __repr__(self):
    return self.ident
    
  def evolve(self, _=None, __=None):
    #No values to mutate in a variable
    return False
      
  @staticmethod
  def generate(available_features, resulttype, unused_min_val=None, 
               unused_max_val=None):
      if not available_features:
          raise NoFeatureAvailable
      
      name = random.choice(available_features)
      newformula = FormulaVariable(name)
      newformula.set_available_features(available_features)
      newformula.resulttype = resulttype
      return newformula

      
class FormulaInteger(Formula):
  def __init__(self, value):
    self.value=value
    self._available_features = None
    self.resulttype = IntegerResult
    
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
    
    
  @staticmethod
  def generate(available_features, resulttype, min_val, max_val):
      if resulttype != IntegerResult:
          raise WrongResultTypeError
      
      newformula = FormulaInteger(0)
      newformula.mutateValue(min_val, max_val)
      newformula.set_available_features(available_features)
      newformula.resulttype = resulttype
      return newformula
       

      
class FormulaBool(Formula):
  def __init__(self, value):
    self.value=value
    self._available_features = None
    self.resulttype = BooleanResult
    
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
    
      
  @staticmethod
  def generate(available_features, resulttype, unused_min_val=None, unused_max_val=None):
      if resulttype != BooleanResult:
          raise WrongResultTypeError
      
      newformula = FormulaBool(True)
      newformula.evolve()
      newformula.set_available_features(available_features)
      newformula.resulttype = resulttype
      return newformula
  
  def to_python_string(self):
      if self.value:
          return "True"
      else:
          return "False"
      
      
class FormulaFloat(Formula):
  def __init__(self, value):
    self.value=value
    self._available_features = None
    self.resulttype = DoubleResult
    
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
      
      
  @staticmethod
  def generate(available_features, resulttype, min_val, max_val):
      if resulttype != DoubleResult:
          raise WrongResultTypeError
      
      newformula = FormulaFloat(0)
      newformula.mutateValue(min_val, max_val)
      newformula.set_available_features(available_features)
      newformula.resulttype = resulttype
      return newformula
 
  
  
  
    
class FormulaBinop(Formula):
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
    if (op in self.comparison_operators) or (op in self.binary_logic_operators):
        self.resulttype = BooleanResult
    else:
        #Arithmetic operator
        if left.resulttype == DoubleResult or right.resulttype == DoubleResult:
            self.resulttype = DoubleResult
        else:
            self.resulttype = IntegerResult
    
  def __repr__(self):
    if not (isImmediate(self.left) and isImmediate(self.right)):
      #Return extended representation
      reprStr = "("+ str(self.left) +" "+ str(self.op) + " " + str(self.right)+")"
      return reprStr
    else:
      #Constant folding
      #Handle special cases where sintax is different
      try:
          e=eval(self.to_python_string())
      except ZeroDivisionError:
          #Ooop... the formula is not so good!
          #Let's return a fallback
          if self.resulttype == BooleanResult:
              return "false"          
          return "0"
          
      s=str(e)
      
      if s == "True":
          return "true"
      elif s == "False":
          return "false"
      else:
          return s
        
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
      newsubformula = generate(self._available_features, self.resulttype,
                               min_val, max_val)
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
  
      
  @classmethod
  def generate(cls, available_features, resulttype, min_val, max_val):
      if resulttype == BooleanResult:
          (op, left, right) = cls._generate_boolean(available_features)
      else:
          (op, left, right) = cls._generate_numeric(available_features, 
                                                    min_val, 
                                                    max_val)
          
      newformula = FormulaBinop(op, left, right)
      newformula.set_available_features(available_features)
      newformula.resulttype = resulttype
      return newformula
  
  @classmethod
  def _generate_boolean(cls, available_features):
      op_class = random.choice([cls.comparison_operators, 
                                cls.binary_logic_operators])
      op = random.choice(op_class)
      
      if op_class == cls.comparison_operators:
          #Need numeric values to compare
          #TODO: allow generation of Float results
          left = generate(available_features, IntegerResult)
          right = generate(available_features, IntegerResult)
      else:
          #Need boolean values
          left = generate(available_features, BooleanResult)
          right = generate(available_features, BooleanResult)
      
      return (op, left, right)
      
      
  @classmethod
  def _generate_numeric(cls, available_features, min_val, max_val):
      op = random.choice(cls.arithmetic_operators)
      #TODO: allow generation of Float results
      left = generate(available_features, IntegerResult, min_val, max_val)
      right = generate(available_features, IntegerResult, min_val, max_val)
      return (op, left, right)
      
  def to_python_string(self):
      s = "(%s %s %s)" % (self.left.to_python_string(),
                          self._pythonOperator(),
                          self.right.to_python_string())
      
      if isImmediate(self.left) and isImmediate(self.right):
          return str(eval(s, {}, {}))
      
      return s
      
  
  
  
class FormulaIf(Formula):
  def __init__(self, cond, thenClause, elseClause=None):
    self.cond = cond
    self.thenClause = thenClause
    self.elseClause = elseClause
    self._available_features = None
    
    typeThen = thenClause.resulttype
    if elseClause:
        typeElse = elseClause.resulttype
    else:
        typeElse = None
        
    #Get the highest-type result type
    if typeThen == DoubleResult or typeElse == DoubleResult:
        self.resulttype = DoubleResult
    elif typeThen == IntegerResult or typeThen == IntegerResult:
        self.resulttype = IntegerResult
    else:
        self.resulttype = BooleanResult
    
        
    
  def __repr__(self):
    #Constant folding
    if str(self.cond) == "true":
        return str(self.thenClause)
    elif str(self.cond) == "false":
        return str(self.elseClause)
        
    thenPart = "(%s)" % str(self.thenClause)
        
    if self.elseClause is not None:
      elseRepr = str(self.elseClause)
      elsePart=" else (%s)" % elseRepr
    else:
      elseRepr=""
      elsePart=""
      
    if thenPart == elseRepr:
        #Both cases are equal: the if clause is useless
        return thenPart

    return "(if " + str(self.cond) + " then " + thenPart + elsePart + ")"
  
  
  def mutate(self, min_val, max_val):
      newsubformula = generate(self._available_features, self.resulttype, 
                               min_val, max_val)
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
      if self.elseClause:
          self.elseClause.set_available_features(available_features)
  
      
  @staticmethod
  def generate(available_features, resulttype, min_val, max_val):
      condition = generate(available_features, BooleanResult)
      thenClause = generate(available_features, resulttype, min_val, max_val)
      elseClause = generate(available_features, resulttype, min_val, max_val)
      
      newformula = FormulaIf(condition, thenClause, elseClause)
      newformula.set_available_features(available_features)
      newformula.resulttype = resulttype
      return newformula

      
  def to_python_string(self):
      assert(self.elseClause is not None)
      s = "(%s if (%s) else (%s))" % (self.thenClause.to_python_string(),
                                      self.cond.to_python_string(),
                                      self.elseClause.to_python_string())
      
      try:
          return str(eval(s, {}, {}))
      except NameError:
          return s
      
  
