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

#define countfeature(type) \
  feature[prefix + RIRNode::typeStr((type)) + "_count"] = \
    bodyir->subnodeCount((type))
  
  
petabricks::ValueMap petabricks::get_rirnode_count_features(
                                                      RIRBlockCopyRef bodyir,
                                                      std::string prefix) {
  ValueMap feature;
  if (prefix!="") prefix=prefix+"_";
  
  countfeature(RIRNode::EXPR_NIL);
  countfeature(RIRNode::EXPR_OP);
  countfeature(RIRNode::EXPR_LIT);
  countfeature(RIRNode::EXPR_IDENT);
  countfeature(RIRNode::EXPR_CHAIN);
  countfeature(RIRNode::EXPR_CALL);
  countfeature(RIRNode::EXPR_ARGS);
  countfeature(RIRNode::EXPR_KEYWORD);
  countfeature(RIRNode::STMT_BASIC);
  countfeature(RIRNode::STMT_BLOCK);
  countfeature(RIRNode::STMT_RAW);
  countfeature(RIRNode::STMT_LOOP);
  countfeature(RIRNode::STMT_COND);
  countfeature(RIRNode::STMT_SWITCH);
  
  return feature;

}
