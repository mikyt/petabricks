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

namespace petabricks {
typedef std::map<std::string, double> ValueMap;

class Heuristic : public jalib::JRefCounted {
  friend class HeuristicManager;
  
public:
  Heuristic(const std::string formula) :
        _formula(MaximaWrapper::instance().runCommandSingleOutput(formula)),
        _min( -std::numeric_limits<double>::infinity()),
        _max( std::numeric_limits<double>::infinity()),
        _uses(0),
        _tooLow(0),
        _tooHigh(0) {}
  
  /** Return the formula that has actually been used for this heuristic.
   * This is either the formula itself or, if it was a constant and lower than 
   * _min or higher than _max, the value of _min or _max respectively */
  FormulaPtr usedFormula() const;
  
  /** Evaluate the heuristic using the given features. If the result is lower 
   * than _min or higher than _max, return _min or _max respectively. 
   * As a side effect, increase the usage count of the heuristic, and, if needed
   * mark the heuristic as being evaluated out of bounds */
  double eval (const ValueMap featureValues=ValueMap());
  
  unsigned int uses() const { return _uses; }
  unsigned int tooLow() const { return _tooLow; }
  unsigned int tooHigh() const { return _tooHigh; }
  
  double getMin() { return _min; }
  double getMax() { return _max; }
  
  std::set<std::string>& getFeatureSet() { return _features; }
  
private:
  /** Eval the heuristic using the given features. Return the exact result,
   * not limited by _max and _min */
  double evalWithoutLimits(const ValueMap featureValues) const;
  
  void setMin(const double min) { _min = min; }
  void setMax(const double max) { _max = max; }
  
  void recordAvailableFeatures(const ValueMap featureValues);
  
private:
  FormulaPtr _formula;
  double _min;
  double _max;
  unsigned int _uses;
  unsigned int _tooLow;
  unsigned int _tooHigh;
  std::set<std::string> _features;
};


typedef jalib::JRef<Heuristic> HeuristicPtr;
typedef std::map<std::string, HeuristicPtr> HeuristicMap;


}

#endif