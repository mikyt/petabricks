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
#ifndef HEURISTICMANAGER_H
#define HEURISTICMANAGER_H

#include <map>

#include "common/jrefcounted.h"
#include "common/jassert.h"

#include "heuristic.h"
#include "dbmanager.h"
#include "maximawrapper.h"

namespace petabricks {

class HeuristicManager;
typedef jalib::JRef<HeuristicManager> HeuristicManagerPtr;

class HeuristicManager : public jalib::JRefCounted {  
  public:
  HeuristicManager(std::string db_filename="") : _db(db_filename) {};
  
  ///Singleton instance
  static HeuristicManager& instance() { JASSERT(_singleton_instance)
                                            .Text("Singleton not initialized!");
                                        return *_singleton_instance; }
  
  ///Init the singleton instance
  ///
  ///Call this once, before using the HeuristicManager                                            
  static void init(std::string db_filename="") {
    _singleton_instance = new HeuristicManager(db_filename);
  }
  
  void registerDefault(const std::string name, const std::string formula) {
          _defaultHeuristics[name] = HeuristicPtr(new Heuristic(formula));
        }
  void loadFromFile(const std::string fileName);
  
  HeuristicPtr& getDefaultHeuristic(const std::string name);
  HeuristicPtr& getHeuristic(const std::string name);
  
  void setMin(const std::string heuristicName, const double min) { 
                              internal_getHeuristic(heuristicName)->setMin(min); 
                            }
              
  void setMax(const std::string heuristicName, const double max) {
                              internal_getHeuristic(heuristicName)->setMax(max);
                            }
  
  const HeuristicMap& usedHeuristics() const { return _usedHeuristics; }
  void useDefaultHeuristics(const bool useDefaultHeuristics) {
    _useDefaultHeuristics = useDefaultHeuristics;
  }
  
private: 
  HeuristicPtr& internal_getDefaultHeuristic(const std::string name);
  HeuristicPtr& internal_getHeuristic(const std::string name);
  
private:
  static HeuristicManagerPtr _singleton_instance;
  HeuristicMap _heuristicCache;
  HeuristicMap _defaultHeuristics;
  HeuristicMap _usedHeuristics;
  HeuristicMap _fromFile;
  DBManager _db;
  bool _useDefaultHeuristics;
};

}

#endif