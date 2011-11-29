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
#include "ruleir.h"

#include <algorithm>


//defined in ruleirparser.{ypp,cpp}
petabricks::RIRBlockCopyRef parseRuleBody(const std::string& str, const jalib::SrcPosTaggable* pos);

petabricks::RIRBlockCopyRef petabricks::RIRBlock::parse(const std::string& str, const jalib::SrcPosTaggable* pos){
  return parseRuleBody(str, pos);
}
petabricks::RIRStmtCopyRef petabricks::RIRStmt::parse(const std::string& str, const jalib::SrcPosTaggable* pos){
  RIRBlockCopyRef t = RIRBlock::parse(str, pos);
  DISABLESRCPOS();
  JASSERT(t->stmts().size()==1)(t->stmts().size());
  return t->stmts().front();
}
petabricks::RIRExprCopyRef petabricks::RIRExpr::parse(const std::string& str, const jalib::SrcPosTaggable* pos){
  RIRStmtCopyRef t = RIRStmt::parse(str+";", pos);
  DISABLESRCPOS();
  JASSERT(t->numExprs()==1)(t->numExprs());
  return t->part(0);
}
  

namespace{ 
  template<typename T> T& get(std::list<T>& lst, int n) {
    typename std::list<T>::iterator i=lst.begin();
    for(; n>0; --n,++i) ; 
    return *i;
  }
}

const char* petabricks::RIRNode::typeStr() const {
  switch(type()){
    case EXPR        : return "EXPR";
    case EXPR_NIL    : return "EXPR_NIL";
    case EXPR_OP     : return "EXPR_OP";
    case EXPR_LIT    : return "EXPR_LIT";
    case EXPR_IDENT  : return "EXPR_IDENT";
    case EXPR_CHAIN  : return "EXPR_CHAIN";
    case EXPR_CALL   : return "EXPR_CALL";
    case EXPR_ARGS   : return "EXPR_ARGS";
    case EXPR_KEYWORD: return "EXPR_KEYWORD";
    case STMT        : return "STMT";
    case STMT_BASIC  : return "STMT_BASIC";
    case STMT_BLOCK  : return "STMT_BLOCK";
    case STMT_RAW    : return "STMT_RAW";
    case STMT_LOOP   : return "STMT_LOOP";
    case STMT_COND   : return "STMT_COND";
    case STMT_SWITCH : return "STMT_SWITCH";
    case BLOCK       : return "BLOCK";
    default          : return "INVALID";
  }
}

template<typename A>
static void pvHook(A& a, std::ostream& o, petabricks::RIRVisitor* v){
    if(v!=NULL)
      a->accept(*v);
    else
      o<<a;
}
template<typename A>
static void pvHook(A& a, std::ostream& o, petabricks::RIRVisitor* v, const char* delim){
  for(typename A::iterator i=a.begin(); i!=a.end(); ++i){
    if(i!=a.begin()) 
      o<<delim;
    pvHook((*i), o, v);
  }
}


void petabricks::RIRExpr::print(std::ostream& o, RIRVisitor* v) {
  o << _str;
  pvHook(_parts, o, v, " ");
}
void petabricks::RIRArgsExpr::print(std::ostream& o, RIRVisitor* v) {
  pvHook(_parts, o, v, ", ");
}
void petabricks::RIRCallExpr::print(std::ostream& o, RIRVisitor* v) {
  JASSERT(_parts.size()>=2)(_parts.size())(_str);
  for(size_t i=0; i<_parts.size()-1; ++i)
    pvHook(get(_parts,i),o,v);
  o << '(';
  pvHook(get(_parts,_parts.size()-1),o,v);
  o << ')';
}
void petabricks::RIRBlock::print(std::ostream& o, RIRVisitor* v) {
  pvHook(_stmts, o, v, "\n");
}
void petabricks::RIRBasicStmt::print(std::ostream& o, RIRVisitor* v) {
  pvHook(_exprs, o, v, " ");
  o<<";";
}
void petabricks::RIRBlockStmt::print(std::ostream& o, RIRVisitor* v) {
  JASSERT(_exprs.size()==0);
  o << "{\n";
  pvHook(_block,o,v);
  o << "\n}";
}
void petabricks::RIRLoopStmt::print(std::ostream& o, RIRVisitor* v) {
  JASSERT(_exprs.size()>=3);
  o << "for("  ; pvHook(get(_exprs,0),o,v); o<< "; ";
                 pvHook(get(_exprs,1),o,v); o<< "; ";
                 pvHook(get(_exprs,2),o,v); o<< ") ";
                 pvHook(_body, o, v);
}
void petabricks::RIRSwitchStmt::print(std::ostream& o, RIRVisitor* v) {
  JASSERT(_exprs.size()==1);
  o << "switch(" ;
  pvHook(_exprs.front(),o,v); 
  o << ") ";
  pvHook(_body, o,v);
}
void petabricks::RIRIfStmt::print(std::ostream& o, RIRVisitor* v) {
  JASSERT(_exprs.size()==1);
  o << "if(" ; 
  pvHook(_exprs.front(),o,v); 
  o << ")\n" ;
  pvHook(_then,o,v);
  if (_else){
    o << "\nelse\n";
    pvHook(_else,o,v);
  }
}
void petabricks::RIRRawStmt::print(std::ostream& o, RIRVisitor*) {
  o << _src;
}

namespace{
  template<typename T>
  void _visithelper(petabricks::RIRVisitor& v, T& t){
    v._before(t);
    if(t && v.shouldDescend(*t)) t->accept(v);
    v._after(t);
  }
  template<typename T>
  void _visitlisthelper(petabricks::RIRVisitor& v, std::list<T>& bk){
    std::list<T> fwd;
    bk.swap(fwd);
    v.pushSplicer(&bk, &fwd);
    while(!fwd.empty()){
      T p = fwd.front(); 
      fwd.pop_front();
      _visithelper(v, p);
      if(p) bk.push_back(p);
    }
    v.popSplicer(&bk, &fwd);
  }

}

void petabricks::RIRExpr::accept(petabricks::RIRVisitor& v) { 
  _visitlisthelper(v, _parts);
}
void petabricks::RIRStmt::accept(petabricks::RIRVisitor& v) {
  _visitlisthelper(v, _exprs);
}
void petabricks::RIRBlock::accept(petabricks::RIRVisitor& v) {
  _visitlisthelper(v, _stmts);
}
void petabricks::RIRBasicStmt::accept(petabricks::RIRVisitor& v) {
  RIRStmt::accept(v);
}
void petabricks::RIRBlockStmt::accept(petabricks::RIRVisitor& v) {
  RIRStmt::accept(v);
  _visithelper(v, _block);
}
void petabricks::RIRLoopStmt::accept(petabricks::RIRVisitor& v) {
  RIRStmt::accept(v);
  _visithelper(v, _body);
}
void petabricks::RIRIfStmt::accept(petabricks::RIRVisitor& v) {
  RIRStmt::accept(v);
  _visithelper(v, _then);
  if(_else) _visithelper(v, _else);
}
void petabricks::RIRSwitchStmt::accept(petabricks::RIRVisitor& v) {
  RIRStmt::accept(v);
  _visithelper(v, _body);
}
void petabricks::RIRRawStmt::accept(petabricks::RIRVisitor& v) {
  RIRStmt::accept(v);
}

petabricks::RIRExpr      * petabricks::RIRExpr      ::clone() const { return new RIRExpr      (*this); }
petabricks::RIRBlock     * petabricks::RIRBlock     ::clone() const { return new RIRBlock     (*this); }
petabricks::RIRBasicStmt * petabricks::RIRBasicStmt ::clone() const { return new RIRBasicStmt (*this); }
petabricks::RIRBlockStmt * petabricks::RIRBlockStmt ::clone() const { return new RIRBlockStmt (*this); }
petabricks::RIRLoopStmt  * petabricks::RIRLoopStmt  ::clone() const { return new RIRLoopStmt  (*this); }
petabricks::RIRIfStmt    * petabricks::RIRIfStmt    ::clone() const { return new RIRIfStmt    (*this); }
petabricks::RIRRawStmt   * petabricks::RIRRawStmt   ::clone() const { return new RIRRawStmt   (*this); }
petabricks::RIRSwitchStmt* petabricks::RIRSwitchStmt::clone() const { return new RIRSwitchStmt(*this); }
petabricks::RIRCallExpr  * petabricks::RIRCallExpr  ::clone() const { return new RIRCallExpr  (*this); }
petabricks::RIRArgsExpr  * petabricks::RIRArgsExpr  ::clone() const { return new RIRArgsExpr  (*this); }

std::string petabricks::RIRNode::debugStr() const { 
  return typeStr(); 
}
std::string petabricks::RIRExpr::debugStr() const { 
  return typeStr() + std::string(" ") + _str;
}

bool petabricks::RIRBlockStmt::containsLeaf(const char* val) const{
  return RIRStmt::containsLeaf(val)
      || _block->containsLeaf(val);
}

const petabricks::RIRExprCopyRef& petabricks::RIRStmt::part(int n) const { 
  JASSERT((int)_exprs.size()>n)(n)(_exprs.size());
  RIRExprList::const_iterator i = _exprs.begin();
  std::advance(i, n);
  return *i;
}
petabricks::RIRExprCopyRef& petabricks::RIRStmt::part(int n) { 
  JASSERT((int)_exprs.size()>n)(n)(_exprs.size());
  RIRExprList::iterator i = _exprs.begin();
  std::advance(i, n);
  return *i;
}

std::string petabricks::RIRLoopStmt::getLimit() {
  std::string inductionVar = getInductionVariable();
  
  RIRExprCopyRef& test = testPart();
  
  if(!test) {
    //There is no explicit limit to the loop!
    return "";
  }
  
  JASSERT(test->isComparison())(test);
  std::string compOp = test->getComparisonOp();
  RIRExprCopyRef LHS = test->getLHS(compOp);
  RIRExprCopyRef RHS = test->getRHS(compOp);
          
  if(LHS->toString() == inductionVar) {
    return RHS->toString();
  }
  else if(RHS->toString() == inductionVar) {
    return LHS->toString();
  }
  
  UNIMPLEMENTED();
  abort(); //Implement this case
}


void petabricks::RIRLoopStmt::computeInductionVariable() {
  RIRExprCopyRef& increment = incPart();
  
  //Force new computation of the induction varible
  _iterationDirection = '\0';
  
  if(increment->type()==EXPR_CHAIN) {
    computeInductionVariableFromIncrement();
  }
  
  if(_iterationDirection=='\0') {
    computeInductionVariableFromBody();
  }
}


///Returns the name of the induction variable or "" if it is impossible to find it here
///It also sets the iteration direction of the found induction variable ('\0' if not found)
void petabricks::RIRLoopStmt::computeInductionVariableFromIncrement(RIRExprCopyRef increment) {
  if(increment->containsLeaf(",")) {
    /* The increment part contains multiple expressions. 
     * Recursively look for the induction variable in all of them */
    computeInductionVariableFromIncrement(increment->getLHS(","));
    computeInductionVariableFromIncrement(increment->getRHS(","));
    return;
  }
  
  if(increment->partsNumber() == 2) {
    RIRExprCopyRef const& part0 = increment->part(0);
    RIRExprCopyRef const& part1 = increment->part(1);

    if(part1->isLeaf("++")) {
      // Case: i++
      _inductionIncrement = increment->toString();
      _iterationDirection = '+';
      _inductionVariable = part0->toString();
      return;
    }
    else if(part0->isLeaf("++")) {
      // Case ++i
      _inductionIncrement = increment->toString();
      _iterationDirection = '+';
      _inductionVariable = part1->toString();
      return;
    }
    else if(part1->isLeaf("--")) {
      // Case: i--
      _inductionIncrement = increment->toString();
      _iterationDirection = '-';
      _inductionVariable = part0->toString();
      return;
    }
    else if(part0->isLeaf("--")) {
      // Case --i
      _inductionIncrement = increment->toString();
      _iterationDirection = '-';
      _inductionVariable = part1->toString();
      return;
    }
    
    UNIMPLEMENTED();
    abort(); //Implement this case
  }
  else if(increment->partsNumber() == 3) {
    RIRExprCopyRef const& part0 = increment->part(0);
    RIRExprCopyRef const& part1 = increment->part(1);
    
    if (part1->isLeaf("+=")) {
      _inductionIncrement = increment->toString();
      _iterationDirection = '+';
      _inductionVariable = part0->toString();
      return;
    }
    else if (part1->isLeaf("-=")) {
      _inductionIncrement = increment->toString();
      _iterationDirection = '-';
      _inductionVariable = part0->toString();
      return;
    }
    else if (part1->isLeaf("*=") || part1->isLeaf("/=")) {
      //NOT a valid induction variable
      _iterationDirection = '\0';
      return;
    }
  }
  else if(increment->partsNumber() == 5) {
    RIRExprCopyRef const& part1 = increment->part(1);
    
    if(part1->isLeaf("=")) {
      RIRExprCopyRef const& part0 = increment->part(0);
      RIRExprCopyRef const& part2 = increment->part(2);
      RIRExprCopyRef const& part3 = increment->part(3);
      RIRExprCopyRef const& part4 = increment->part(4);
      
 
      if(   (part0->toString() == part2->toString() && part4->type() == EXPR_LIT)  //Case: i = i + c
         || (part0->toString() == part4->toString() && part2->type() == EXPR_LIT)) //Case: i = c + i
      {
        if(part3->isLeaf("+")) {
          _inductionIncrement = increment->toString();
          _iterationDirection='+';
          _inductionVariable = part0->toString();
          return;
        }
        else if (part3->isLeaf("-")) {
          _inductionIncrement = increment->toString();
          _iterationDirection='-';
          _inductionVariable = part0->toString();
          return;
        }
      }
    }
  }
  
  JWARNING(false && "InductionVariableIdentifier - Should handle this case better")(increment->typeStr())(increment);
  UNIMPLEMENTED(); abort(); //Implement this case
}  



void petabricks::RIRLoopStmt::computeInductionVariableFromBody() {
  InductionVariableIdentifier identifierVisitor;
  
  _iterationDirection = identifierVisitor.getIterationDirectionFromBody(*this);
  _inductionIncrement = identifierVisitor.getInductionIncrementFromBody(*this);
  _inductionVariable = identifierVisitor.getInductionVariableFromBody(*this);
}


bool petabricks::RIRExpr::containsBoolOp() const {
  if(   containsLeaf("&&") 
     || containsLeaf("&")
     || containsLeaf("||")
     || containsLeaf("|")
     || containsLeaf("!")
     || containsLeaf("^")) {
       return true;
     }
  return false;
}

petabricks::RIRExprCopyRef petabricks::RIRExpr::getLHS(std::string splitToken) const {
  JASSERT(isAssignment() || isComparison() || containsLeaf(","));
  
  RIRExprCopyRef lhs(new RIRExpr(EXPR_CHAIN));
  
  for(RIRExprList::const_iterator i=_parts.begin(), e=_parts.end(); i!=e; ++i) {
    if((*i)->isLeaf(splitToken.c_str())) {
      return lhs;
    }
    
    lhs->addSubExpr(*i);
  }
  
  //Should never reach here: is the expression really an assigment?
  abort();
}



petabricks::RIRExprCopyRef petabricks::RIRExpr::getRHS(std::string splitToken) const {
  JASSERT(isAssignment() || isComparison() || containsLeaf(","));
  
  RIRExprCopyRef rhs(new RIRExpr(EXPR_CHAIN));
  
  ///Reach the "=" sign
  RIRExprList::const_iterator i;
  for(i=_parts.begin(); ! (*i)->isLeaf(splitToken.c_str()); ++i);
  
  //Get first rhs part
  ++i;
  
  for(RIRExprList::const_iterator e=_parts.end(); i!=e; ++i) {
    rhs->addSubExpr(*i);
  }
  
  return rhs;
}


#define checkOp(op) if(containsLeaf(op)) { return op; }
std::string petabricks::RIRExpr::getComparisonOp() const {
  /* TODO: an expression could contain multiple comparison operators
   * such as in:
   * (a==b) && (c<d)
   * This is not supported yet! Only a single comparison operator is supported
   */
  
  checkOp("==");
  checkOp("!=");
  checkOp(">=");
  checkOp("<=");
  checkOp("<");
  checkOp(">");
  
  return "";
}


void petabricks::RIRLoopStmt::InductionVariableIdentifier::computeInductionVariableAndIterationDirectionFromBody(RIRLoopStmt& loop) {
  RIRStmtCopyRef& loopBody = loop.body();
  loopBody->accept(*this);
  
  //Remove variables with more than one assignment: thay cannot be induction variables
  CounterMap::iterator i=_variableAssignmentNumber.begin(), e=_variableAssignmentNumber.end(), next;
  while(i != e) {
    JTRACE("assignment")(i->first)(i->second.count)(i->second.iterationDirection);
    if(i->second.count != 1) {
      next=i;
      next++;
      
      _variableAssignmentNumber.erase(i);
      i=next;
    }
    else {
      ++i;
    }
  }
  
  CounterMap::iterator indVar;
  if(_variableAssignmentNumber.size() == 0) {
    //No induction variable here!
    JWARNING(false && "MissingInductionVariable")(loopBody);
    return;
  }
  if(_variableAssignmentNumber.size() > 1) {
    //Debug print
    JTRACE("Multiple assignments")(loopBody);
    for (CounterMap::iterator i=_variableAssignmentNumber.begin(), e=_variableAssignmentNumber.end(); i!=e; ++i) {
      JTRACE("Assignment")(i->first)(i->second.count)(i->second.iterationDirection);
    }
    
    //Implementation
    //If only one of the candidates appear in the loop condition, it is the induction variable
    RIRExprCopyRef& loopCondition = loop.testPart();
    indVar = _variableAssignmentNumber.end();
    for (CounterMap::iterator i=_variableAssignmentNumber.begin(), e=_variableAssignmentNumber.end(); i!=e; ++i) {
      std::string candidateVarName = i->first;
      if(loopCondition->containsLeaf(candidateVarName.c_str())) {
        if(indVar!=e) {
          //This is not the only single-assigned variable to appear in the condition
          UNIMPLEMENTED();
          abort();
        }
        
        //First single-assigned variable to appear in the condition
        indVar = i;
      }
    }
    
    if(indVar == _variableAssignmentNumber.end()) {
      //No single-assigned variable appears in the condition
      UNIMPLEMENTED();
      abort();
    }
  }
  else {
    //Only one variable with a single assignment: it's the induction variable
    indVar = _variableAssignmentNumber.begin();
  }
  _inductionVariable = indVar->first;
  _iterationDirection = indVar->second.iterationDirection;
  _inductionIncrement = indVar->second.inductionIncrement;
}

void petabricks::RIRLoopStmt::InductionVariableIdentifier::before(RIRExprCopyRef& expr) {
  //Count how many times each variable is assigned
  JTRACE("InductionVisitor")(expr->typeStr())(expr);
  if(expr->type() != EXPR_CHAIN || expr->partsNumber()==1) {
    //We don't care about this
    return;
  }
  
  if(expr->partsNumber()==2) {
    if(expr->part(0)->isLeaf("++")) {
      //Case: ++i
      increaseCount(expr->part(1)->str(), '+', expr->toString());
      
      return;
    }
    else if(expr->part(1)->isLeaf("++")) {
      //Case: i++
      increaseCount(expr->part(0)->str(), '+', expr->toString());
      return;
    }
    else if(expr->part(0)->isLeaf("--")) {
      //Case: --i
      increaseCount(expr->part(1)->str(), '-', expr->toString());
      
      return;
    }
    else if(expr->part(1)->isLeaf("--")) {
      //Case: i++
      increaseCount(expr->part(0)->str(), '-', expr->toString());
      return;
    }
  }
  else if (expr->partsNumber()>=3) {
    if ( ! expr->isAssignment()) {
      //No assignment here: no induction variable
      return;
    }
    
    if (expr->getLHS()->partsNumber() != 1) {
      //This is not an assignment to a single variable (maybe to a cell of a matrix?)
      return;
    }
    
    if ( ! expr->getRHS()->containsLeaf("+") || ! expr->getRHS()->containsLeaf("-")) {
      //No variable is incremented/decremented. This is just a copy of a value.
      //No induction variable here
      return;
    }
    
    if((expr->part(2)->str() == expr->part(0)->str() || expr->part(4)->str() == expr->part(0)->str())) {
      if (expr->part(3)->isLeaf("+")) {
        //Case: i = i + y
        //Case: i = y + i
        increaseCount(expr->part(0)->str(), '+', expr->toString());
        return;
      }
      else if (expr->part(3)->isLeaf("-")) {
        //Case: i = i - y
        //Case: i = y - i
        increaseCount(expr->part(0)->str(), '-', expr->toString());
        return;
      }
    }
  }
  
  JWARNING(false && "InductionVariableIdentifier - Should handle this case better")(expr->typeStr())(expr);
  abort();
}

unsigned int petabricks::RIRBlockStmt::opsNumber() const { 
    return _block->opsNumber();
}