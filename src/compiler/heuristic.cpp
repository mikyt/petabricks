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
  if (isInCache(featureValues)) {
    countLowAndHigh();
    return _lastValue.d;
  }
  
  //Compute
  evalSideEffects(featureValues);
  
  double value = evalWithoutLimitsDouble(featureValues);
  
  //Keep the value within the limits
  if (value < _min) {
    _highlowstatus = LOW;
    value = _min;
  }
  else if (value > _max) {
    _highlowstatus = HIGH;
    value = _max;
  }
  else {
    _highlowstatus = OK;
  }
  
  //Store in cache
  _cacheIsValid = true;
  _lastValueMap = featureValues;
  _lastValue.d = value;
  _isConstant = _formula->isConstant();
  countLowAndHigh();
  
  setUsedFormula();
  return value;
}

int petabricks::Heuristic::evalInt (const ValueMap& featureValues) {
  if (isInCache(featureValues)) {
    countLowAndHigh();
    return _lastValue.i;
  }
  
  //Compute
  evalSideEffects(featureValues);
  
  int value = evalWithoutLimitsInt(featureValues);
  
  //Keep the value within the limits
  if (value < _min) {
    _highlowstatus = LOW;
    value = _min;
  }
  else if (value > _max) {
    _highlowstatus = HIGH;
    value = _max;
  }
  else {
    _highlowstatus = OK;
  }
  
  //Store in cache
  _cacheIsValid = true;
  _lastValueMap = featureValues;
  _lastValue.i = value;
  _isConstant = _formula->isConstant();
  countLowAndHigh();
  
  setUsedFormula();
  return value;
}


bool petabricks::Heuristic::evalBool(const ValueMap& featureValues) {
  if (isInCache(featureValues)) {
    return _lastValue.b;
  }
  
  //Compute
  evalSideEffects(featureValues);
  
  bool value = evalWithoutLimitsBool(featureValues);
  
  //Store in cache
  _cacheIsValid = true;
  _lastValueMap = featureValues;
  _lastValue.b = value;
  _isConstant = _formula->isConstant();

  setUsedFormula();
  return value;
}


void petabricks::Heuristic::evalSideEffects(const ValueMap& featureValues) {
  recordAvailableFeatures(featureValues);
  _uses++;
}


void petabricks::Heuristic::setUsedFormula() {
  if (! _formula->isConstant()) {
    _usedFormula = _formula;
    return;
  }
  
  if (_type == BOOL) {
    _usedFormula = _formula;
    return;
  }
  
  //The formula is a constant double or int value
  double value;
  if (_type == INT) {
    value = _lastValue.i;
  }
  else {
    value = _lastValue.d;
  }
  
  //Enforce limits
  if(value < _min) {
    value = _min;
  }
  else if(value > _max) {
    value = _max;
  }
  
  _usedFormula = MaximaWrapper::instance().runCommandSingleOutput(jalib::XToString(value));
}


petabricks::FormulaPtr petabricks::Heuristic::evalWithoutLimits_common (const ValueMap& featureValues) const {
  JASSERT(_type != Heuristic::NONE)(_type);
    
  return MaximaWrapper::instance().subst(featureValues, _formula);
}


