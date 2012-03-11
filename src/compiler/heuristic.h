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
#ifndef HEURISTIC_H
#define HEURISTIC_H

#include <limits>
#include <map>

#include "common/jrefcounted.h"
//#include "common/jassert.h"

#include "maximawrapper.h"
#include "featurecomputer.h"

namespace petabricks {

class Heuristic : public jalib::JRefCounted, public jalib::JPrintable {
  friend class HeuristicManager;
  
public:
  enum Type {
    NONE,
    BOOL,
    INT,
    DOUBLE
  };
  
  Heuristic(const std::string formula) :
        _formula(MaximaWrapper::instance().runCommandSingleOutput(formula)),
        _min( -std::numeric_limits<double>::infinity()),
        _max( std::numeric_limits<double>::infinity()),
        _uses(0),
        _tooLow(0),
        _tooHigh(0),
        _type(NONE) {}
  
  /** Return the formula that has actually been used for this heuristic.
   * This is either the formula itself or, if it was a constant and lower than 
   * _min or higher than _max, the value of _min or _max respectively */
  FormulaPtr usedFormula() const;
  
  /** Evaluate the heuristic using the given features. If the result is lower 
   * than _min or higher than _max, return _min or _max respectively. 
   * As a side effect, increase the usage count of the heuristic, and, if needed
   * mark the heuristic as being evaluated out of bounds */
  double evalDouble (const ValueMap& featureValues=ValueMap());
  
  /** Evaluate the heuristic using the given features. If the result is lower 
   * than _min or higher than _max, return _min or _max respectively. 
   * As a side effect, increase the usage count of the heuristic, and, if needed
   * mark the heuristic as being evaluated out of bounds */
  
  int evalInt(const ValueMap& featureValues=ValueMap());
  
  /** Evaluate the heuristic using the given features, returning the 
   * corresponding boolean result.
   * 
   * As a side effect, increase the usage count of the heuristic */
  bool evalBool (const ValueMap& featureValues=ValueMap());
  
  
  unsigned int uses() const { return _uses; }
  unsigned int tooLow() const { return _tooLow; }
  unsigned int tooHigh() const { return _tooHigh; }
  
  double getMin() const { return _min; }
  double getMax() const { return _max; }
  Type getType() const { return _type; }
  
  std::string getTypeStr () { switch(_type) {
                                case NONE:
                                  return "none";
                                case BOOL:
                                  return "bool";
                                case INT:
                                  return "int";
                                case DOUBLE:
                                  return "double";
                                default:
                                  JNOTE("Should not arrive here!")(_type);
                                  abort();
                              }
                            }
  
  std::set<std::string>& getFeatureSet() { return _features; }
  
  void print(std::ostream& o) const {
    FormulaPtr usedformula = usedFormula();

    if (! usedformula->isConstant()) {
      o << usedformula->toString();
      return;
    }
    
    if (!_type==BOOL) {
      o << usedformula->toString();
      return;
    }

    if (MaximaWrapper::instance().toBool(usedformula)->valueBool()) {
      o << "true";
      return;
    }
    
    o << "false";
  }
  
private:
  /** Eval the heuristic using the given features. Return the exact result,
   * not limited by _max and _min */
  
  double evalWithoutLimitsDouble(const ValueMap& featureValues) const {
                                  JASSERT(getType()== DOUBLE);
                                  return evalWithoutLimitsNumber(featureValues);
                                }
    
  int evalWithoutLimitsInt(const ValueMap& featureValues) const {
                            JASSERT(getType() == INT);
                            return int(evalWithoutLimitsNumber(featureValues));
                          } 
  
  double evalWithoutLimitsNumber(const ValueMap& featureValues) const {
                  FormulaPtr evaluated(evalWithoutLimits_common(featureValues));
                  evaluated = MaximaWrapper::instance().toFloat(evaluated);
                  double value = evaluated->valueDouble();
                  
                  JTRACE("Evaluated number")(value);
                  return value;
                }
                 
  bool evalWithoutLimitsBool(const ValueMap& featureValues) const {
                  JASSERT(getType() == BOOL);
                  FormulaPtr evaluated(evalWithoutLimits_common(featureValues));
                  evaluated = MaximaWrapper::instance().toBool(evaluated);
                  bool value = evaluated->valueBool();
                  
                  JTRACE("Evaluated bool")(value);
                  return value;
                }
  
  FormulaPtr evalWithoutLimits_common(const ValueMap& featureValues) const;
  
  void evalSideEffects(const ValueMap& featureValues);
  
  void setMin(const double min) { _min = min; }
  void setMax(const double max) { _max = max; }
  void setType(const Type type) { _type = type; }
  
  void recordAvailableFeatures(const ValueMap featureValues);
  
private:
  FormulaPtr _formula;
  double _min;
  double _max;
  unsigned int _uses;
  unsigned int _tooLow;
  unsigned int _tooHigh;
  std::set<std::string> _features;
  Type _type;
};


typedef jalib::JRef<Heuristic> HeuristicPtr;
typedef std::map<std::string, HeuristicPtr> HeuristicMap;


}

#endif