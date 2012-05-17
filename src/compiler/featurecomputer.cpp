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

#include "featurecomputer.h"
#include "tinyxml.h"
#include "common/jconvert.h"

#define countfeature(type) \
  feature[prefix + RIRNode::typeStr((type)) + "_count"] = \
     bodyir ? bodyir->subnodeCount((type)) : 0
  
void petabricks::ValueMap::print(std::ostream& o) const {
  o << "ValueMap ";
  for (ValueMap::const_iterator i=begin(), e=end(); i!=e; ++i) {
    o << i->first;
    o << ":";
    o << jalib::XToString(i->second);
    o << ";  ";
  }
}

petabricks::ValueMap petabricks::get_zero_valued_staticcounter_features(std::string prefix) {
  ValueMap empty;
  #define feature(name) empty[prefix+ #name]=0;
  #include "featurelist.inc"
  #undef feature
  return empty;
}

petabricks::ValueMap petabricks::load_features_from_file(std::string filename) {
  ValueMap values_from_file;
  
  TiXmlDocument doc(filename.c_str());
	bool loaded = doc.LoadFile();

  if( ! loaded) {
    JNOTE("Unable to load features")(filename);
    exit(10);
  }
  TiXmlHandle docHandle( &doc );
	TiXmlElement* feature = docHandle.FirstChildElement("features").FirstChildElement("feature").ToElement();

	while (feature) {
    std::string name = feature->Attribute("name");
    std::string valuetext = feature->Attribute("value");
    double value = jalib::StringToDouble(valuetext);
    
    JTRACE("feature")(name)(value);
    values_from_file[name] = value;
    
    //Next  
    feature = feature->NextSiblingElement("feature");
  }
  return values_from_file;
}