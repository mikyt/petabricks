/*****************************************************************************
 *  Copyright (C) 2008-2011 Massachusetts Institute of Technology            *
 *                                                                           *
 *  Permission is hereby granted, free of charge, to any person obtaining    *
 *  a copy of this software and associated documentation files (the          *
 *  "Software"), to deal in the Software without restriction, including      *
 *  without limitation the rights to use, copy, modify, merge, publish,      *
 *  distribute, sublicense, and/or sell copies of the Software, and to       *
 *  permit persons to whom the Software is furnished to do so, subject       *
 *  to the following conditions:                                             *
 *                                                                           *
 *  The above copyright notice and this permission notice shall be included  *
 *  in all copies or substantial portions of the Software.                   *
 *                                                                           *
 *  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY                *
 *  KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE               *
 *  WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND      *
 *  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE   *
 *  LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION   *
 *  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION    *
 *  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE           *
 *                                                                           *
 *  This source code is part of the PetaBricks project:                      *
 *    http://projects.csail.mit.edu/petabricks/                              *
 *                                                                           *
 *****************************************************************************/
#include "heuristic.h"

void petabricks::Heuristic::recordAvailableFeatures(const ValueMap 
                                                        featureValues) {
  for(ValueMap::const_iterator i=featureValues.begin(),
                               e=featureValues.end();
      i != e;
      ++i) {
    std::string feature_name = i->first;
    _features.insert(feature_name);
  }
}

double petabricks::Heuristic::evalDouble (const ValueMap& featureValues) {
  evalSideEffects(featureValues);
  
  double value = evalWithoutLimitsDouble(featureValues);
  
  //Keep the value within the limits
  if (value < _min) {
    _tooLow++;
    return _min;
  }
  else if (value > _max) {
    _tooHigh++;
    return _max;
  }
  else {
    return value;
  }
}

int petabricks::Heuristic::evalInt (const ValueMap& featureValues) {
  evalSideEffects(featureValues);
  
  int value = evalWithoutLimitsInt(featureValues);
  
  //Keep the value within the limits
  if (value < _min) {
    _tooLow++;
    return _min;
  }
  else if (value > _max) {
    _tooHigh++;
    return _max;
  }
  else {
    return value;
  }
}

bool petabricks::Heuristic::evalBool(const ValueMap& featureValues) {
  evalSideEffects(featureValues);
  
  bool value = evalWithoutLimitsBool(featureValues);
  
  return value;
}

void petabricks::Heuristic::evalSideEffects(const ValueMap& featureValues) {
  recordAvailableFeatures(featureValues);
  _uses++;
}

petabricks::FormulaPtr petabricks::Heuristic::usedFormula() const { 
  if (! _formula->isConstant()) {
    return _formula;
  }
  
  if (_type == BOOL) {
    return _formula;
  }
  
  //The formula is a constant float or int value
  double value;
  if (_type == INT) {
    value = evalWithoutLimitsInt(ValueMap());
  }
  else {
    value = evalWithoutLimitsDouble(ValueMap());
  }
  
  if(value < _min) {
    //Return min
    return MaximaWrapper::instance().runCommandSingleOutput(jalib::XToString(_min));
  }
  if(value > _max) {
    //Return max
    return MaximaWrapper::instance().runCommandSingleOutput(jalib::XToString(_max));
  }
  
  return _formula;
}

petabricks::FormulaPtr petabricks::Heuristic::evalWithoutLimits_common (const ValueMap& featureValues) const {
  JASSERT(_type != Heuristic::NONE)(_type);
  JTRACE("Evaluating formula")(_formula);
  FormulaPtr evaluated = _formula;
  
  for(ValueMap::const_iterator i=featureValues.begin(), e=featureValues.end();
      i!=e;
      ++i) {
    const std::string& featureName=i->first;
    const std::string featureValueStr = jalib::XToString(i->second);
    
    evaluated = MaximaWrapper::instance().subst(featureValueStr, featureName, evaluated);
  }

  return evaluated;
}


