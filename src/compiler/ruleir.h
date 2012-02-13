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
#ifndef PETABRICKSRULEIR_H
#define PETABRICKSRULEIR_H

#include "common/jconvert.h"
#include "common/jprintable.h"
#include "common/jrefcounted.h"
#include "common/srcpos.h"

#include <list>
#include <map>
#include <string>

#ifdef HAVE_CONFIG_H
# include "config.h"
#endif

namespace petabricks {

class RIRNode;
class RIRBlock;
class RIRStmt;
class RIRExpr;
typedef jalib::JRef<RIRNode,  jalib::JRefPolicyCopied<RIRNode>  > RIRNodeCopyRef;
typedef jalib::JRef<RIRBlock, jalib::JRefPolicyCopied<RIRBlock> > RIRBlockCopyRef;
typedef jalib::JRef<RIRStmt,  jalib::JRefPolicyCopied<RIRStmt>  > RIRStmtCopyRef;
typedef jalib::JRef<RIRExpr,  jalib::JRefPolicyCopied<RIRExpr>  > RIRExprCopyRef;
typedef jalib::JRef<RIRNode > RIRNodeRef;
typedef jalib::JRef<RIRBlock> RIRBlockRef;
typedef jalib::JRef<RIRStmt > RIRStmtRef;
typedef jalib::JRef<RIRExpr > RIRExprRef;
typedef std::list<RIRNodeCopyRef>  RIRNodeList;
typedef std::list<RIRStmtCopyRef>  RIRStmtList;
typedef std::list<RIRExprCopyRef>  RIRExprList;

// interface for compiler passes
class RIRVisitor {
public: 
  //hooks called as we walk the tree -- used by compiler passes
  virtual void before(RIRExprCopyRef&)    {}
  virtual void before(RIRStmtCopyRef&)    {}
  virtual void before(RIRBlockCopyRef&)   {}
  virtual void after(RIRExprCopyRef&)     {}
  virtual void after(RIRStmtCopyRef&)     {}
  virtual void after(RIRBlockCopyRef&)    {}

  //base versions of the hooks used by infrastructure
  virtual void _before(RIRExprCopyRef& p)  { before(p); }
  virtual void _before(RIRStmtCopyRef& p)  { before(p); }
  virtual void _before(RIRBlockCopyRef& p) { before(p); }
  virtual void _after(RIRExprCopyRef& p)   { after(p);  }
  virtual void _after(RIRStmtCopyRef& p)   { after(p);  }
  virtual void _after(RIRBlockCopyRef& p)  { after(p);  }
   
  //allow visitor to short circuit over uninteresting nodes
  virtual bool shouldDescend(const RIRNode&) { return true; }

  //splicers allow new code to be inserted into the tree
  virtual void pushSplicer(RIRStmtList* /*bk*/, RIRStmtList* /*fwd*/){}
  virtual void pushSplicer(RIRExprList* /*bk*/, RIRExprList* /*fwd*/){}
  virtual void popSplicer(RIRStmtList*  /*bk*/, RIRStmtList* /*fwd*/){}
  virtual void popSplicer(RIRExprList*  /*bk*/, RIRExprList* /*fwd*/){}
};

/**
 * Base class for all Rule IR types
 */
class RIRNode : public jalib::JRefCounted,
                public jalib::JPrintable,
                public jalib::SrcPosTaggable {
  typedef std::map<std::string, std::string> AnnotationT;
public:

  enum Type {
    INVALID,
    EXPR          = 0x10000,
    EXPR_NIL,
    EXPR_OP,
    EXPR_LIT,
    EXPR_IDENT,
    EXPR_CHAIN,
    EXPR_CALL,
    EXPR_ARGS,
    EXPR_KEYWORD,
    STMT          = 0x20000,
    STMT_BASIC,
    STMT_BLOCK,
    STMT_RAW,
    STMT_LOOP,
    STMT_COND,
    STMT_SWITCH,
    BLOCK         = 0x40000
  };
  RIRNode(Type t) : _type(t) {}
  Type type() const { return _type; }
  const char* typeStr() const;
  static const char* typeStr(const Type t);
  virtual std::string debugStr() const;
  bool isExpr()  const { return (_type&EXPR)  != 0; }
  bool isStmt()  const { return (_type&STMT)  != 0; }
  bool isBlock() const { return (_type&BLOCK) != 0; }
  virtual void accept(RIRVisitor&) = 0;
  virtual RIRNode* clone() const = 0;

  bool isControl() const { return _type==STMT_LOOP || _type==STMT_COND || _type==STMT_SWITCH; }

  virtual void print(std::ostream& o, RIRVisitor* printVisitor) = 0;
  void print(std::ostream& o) const {
    RIRNodeRef t = clone();
    t->print(o, NULL);
  }
  
  void addAnnotation(const std::string& name, const std::string& val=""){
    JWARNING(!hasAnnotation(name))(name);
    _annotations[name]=val;
  }
  void removeAnnotation(const std::string& name){
    JASSERT(hasAnnotation(name))(name);
    _annotations.erase(_annotations.find(name));
  }
  bool hasAnnotation(const std::string& name) const {
    return _annotations.find(name) != _annotations.end();
  }
  const std::string& getAnnotation(const std::string& name) const {
    AnnotationT::const_iterator i = _annotations.find(name);
    JASSERT(i != _annotations.end())(name);
    return i->second;
  }
  
  /** Return the number of subnodes of a given type this node includes.
   * The node itself is counted if it is of the correct type. */
  virtual unsigned int subnodeCount(Type type) const = 0;
  
  /** Return the number of operations executed by this node, approximated
   * by the number of EXPR_OP it contains */
  unsigned int opsNumber() const { return subnodeCount(EXPR_OP); }
protected:
  Type _type;
  AnnotationT _annotations;
};

/**
 * Rule IR Expression Types
 */
class RIRExpr  : public RIRNode {
public:
  static RIRExprCopyRef parse(const std::string& str, const jalib::SrcPosTaggable*);
  RIRExpr(Type t, const std::string& str="") : RIRNode(t), _str(str) {}
  void addSubExpr(const RIRExprCopyRef& p) { _parts.push_back(p); }
  void prependSubExpr(const RIRExprCopyRef& p) { _parts.push_front(p); }
  void print(std::ostream& o, RIRVisitor* printVisitor);
  void accept(RIRVisitor&);
  RIRExpr* clone() const;
  std::string debugStr() const;

  const std::string& str() const
    {
      return _str;
    }

  bool isLeaf(const char* val) const{
    return _parts.empty() && _str==val;
  }
  bool isLeaf() const{
    return _parts.empty();
  }

  bool containsLeaf(const char* val) const{
    if(isLeaf())
      return isLeaf(val);
    for(RIRExprList::const_iterator i=_parts.begin(); i!=_parts.end(); ++i)
      if((*i)->containsLeaf(val))
        return true;
    return false;
  }
  RIRExprList& parts(){ return _parts; }
  RIRExprCopyRef part(int n) const{ 
    JASSERT(n<(int)_parts.size());
    RIRExprList::const_iterator i=_parts.begin();
    while(n-->0) ++i;
    return *i;
  }
  
  ///Return the number of subparts the expression is made of
  size_t partsNumber() const {return _parts.size(); }
  
  ///If the expression is a comparison, returns the comparison operator
  std::string getComparisonOp() const;
  
  ///Return true if the expression is an assignment
  bool isAssignment() const { return containsLeaf("="); }
  
  ///Return true if the expression is a comparison
  bool isComparison() const { return getComparisonOp() != ""; }
  
  ///Return true if the expression contains a boolean operator
  bool containsBoolOp() const;
  
  ///Return true if the expression contains a ternary operator
  bool containsTernaryOp() const { return containsLeaf("?"); }
  
  ///Return the Left Hand Side of an assigment expression
  RIRExprCopyRef getLHS(std::string splitToken = "=") const;
  
  ///Return the Right Hand Side of an assignment expression
  RIRExprCopyRef getRHS(std::string splitToken = "=") const;
  
  virtual unsigned int subnodeCount(Type kind) const {
    unsigned int count = 0;
    if (type()==kind) {
      count ++;
    }
    for (RIRExprList::const_iterator i=_parts.begin(), e=_parts.end();
         i != e;
         ++i) {
      count += (*i)->subnodeCount(kind);
    }
    return count;
  }
protected:
  std::string _str;
  RIRExprList _parts;
};

class RIRCallExpr  : public RIRExpr{
public:
  RIRCallExpr(): RIRExpr(EXPR_CALL) {}
  void print(std::ostream& o, RIRVisitor* printVisitor);
  RIRCallExpr* clone() const;
};

class RIRArgsExpr: public RIRExpr{
public:
  RIRArgsExpr(): RIRExpr(EXPR_ARGS) {}
  void print(std::ostream& o, RIRVisitor* printVisitor);
  RIRArgsExpr* clone() const;
};

#define RIRNilExpr()       RIRExpr(RIRNode::EXPR_NIL)
#define RIROpExpr(s)       RIRExpr(RIRNode::EXPR_OP,s)
#define RIRLitExpr(s)      RIRExpr(RIRNode::EXPR_LIT,s)
#define RIRIdentExpr(s)    RIRExpr(RIRNode::EXPR_IDENT,s)
#define RIRChainExpr()     RIRExpr(RIRNode::EXPR_CHAIN)
#define RIRKeywordExpr(s)  RIRExpr(RIRNode::EXPR_KEYWORD, s)

/**
 * Rule IR Statement types
 */
class RIRStmt  : public RIRNode {
public:
  static RIRStmtCopyRef parse(const std::string& str, const jalib::SrcPosTaggable*);

  RIRStmt(Type t) : RIRNode(t) {}
  void addExpr(const RIRExprCopyRef& p){ _exprs.push_back(p); }
  void accept(RIRVisitor&);
  virtual RIRStmt* clone() const = 0;
  
  virtual bool containsLeaf(const char* val) const{
    for(RIRExprList::const_iterator i=_exprs.begin(); i!=_exprs.end(); ++i)
      if((*i)->containsLeaf(val))
        return true;
    return false;
  }
  
  const RIRExprCopyRef& part(int n) const;
  RIRExprCopyRef& part(int n);
  
  //remove the last Expr and return it
  RIRExprCopyRef popExpr(){
    RIRExprCopyRef t = _exprs.back();
    _exprs.pop_back();
    return t;
  }

  int numExprs() const { return (int)_exprs.size(); }
  
  virtual const RIRBlockCopyRef& extractBlock() const { UNIMPLEMENTED(); return *static_cast<const RIRBlockCopyRef*>(0); }
                                         
  virtual unsigned int subnodeCount(Type kind) const {
                              unsigned int count = 0;
                              if (type() == kind) {
                                count++;
                              }
                              for (RIRExprList::const_iterator i=_exprs.begin(),
                                                               e=_exprs.end();
                                   i != e;
                                   ++i) {
                                count += (*i)->subnodeCount(kind);
                              }
                              return count;
                            }
protected:
  RIRExprList _exprs;
};

class RIRBasicStmt  : public RIRStmt {
public:
  RIRBasicStmt() : RIRStmt(STMT_BASIC) {}
  void print(std::ostream& o, RIRVisitor* printVisitor);
  void accept(RIRVisitor&);
  RIRBasicStmt* clone() const;
};

class RIRControlStmt  : public RIRStmt {
public:
  RIRControlStmt(Type t) : RIRStmt(t) {}
};

class RIRLoopStmt: public RIRControlStmt{
  class InductionVariableIdentifier : public RIRVisitor, public jalib::SrcPosTaggable {
    struct IndVarCandidate {
      unsigned int count;
      char iterationDirection;
      std::string inductionIncrement;
    };
    typedef std::map <std::string, IndVarCandidate> CounterMap;
    
  public:
    InductionVariableIdentifier () : _iterationDirection('\0'), _inductionVariable(""), _inductionIncrement("") {}
    
    std::string getInductionVariableFromBody(RIRLoopStmt& loop) {
      if (_iterationDirection == '\0') {
        computeInductionVariableAndIterationDirectionFromBody(loop);
      }
      return _inductionVariable;
    }
    
    char getIterationDirectionFromBody(RIRLoopStmt& loop) {
      if (_iterationDirection == '\0') {
        computeInductionVariableAndIterationDirectionFromBody(loop);
      }
      return _iterationDirection;
    }
    
    std::string getInductionIncrementFromBody(RIRLoopStmt& loop) {
      if (_iterationDirection == '\0') {
        computeInductionVariableAndIterationDirectionFromBody(loop);
      }
      return _inductionIncrement;
    }
  
  private: //Methods
    virtual void before(RIRExprCopyRef&);
    
    void computeInductionVariableAndIterationDirectionFromBody(RIRLoopStmt& loop);
    
    ///Record a new assignment for a given variable
    void increaseCount (std::string variableName, char iterationDirection, std::string inductionIncrement) {
      CounterMap::iterator varIt;
      if((varIt = _variableAssignmentNumber.find(variableName)) != _variableAssignmentNumber.end()) {
        //Previously assigned variable
        varIt->second.count ++;
        varIt->second.iterationDirection = iterationDirection;
        varIt->second.inductionIncrement = inductionIncrement;
      }
      else {
        //New variable
        IndVarCandidate& var = _variableAssignmentNumber[variableName];
        var.count = 1;
        var.iterationDirection = iterationDirection;
        var.inductionIncrement = inductionIncrement;
      }
    }
    
  private:
    CounterMap _variableAssignmentNumber;
    
    //Cached results
    char _iterationDirection;
    std::string _inductionVariable;
    std::string _inductionIncrement;
  };
public:
  RIRLoopStmt(const RIRStmtCopyRef& p) : RIRControlStmt(STMT_LOOP) { _body=p; }
  void print(std::ostream& o, RIRVisitor* printVisitor);
  void accept(RIRVisitor&);
  RIRLoopStmt* clone() const;
  bool containsLeaf(const char* val) const{
    return RIRStmt::containsLeaf(val)
        || _body->containsLeaf(val);
  }
  const RIRExprCopyRef& declPart() const { return part(0); }
  const RIRExprCopyRef& testPart() const { return part(1); }
  const RIRExprCopyRef& incPart() const { return part(2); }
  const RIRStmtCopyRef& body() const { return _body; }
  RIRExprCopyRef& declPart() { return part(0); }
  RIRExprCopyRef& testPart() { return part(1); }
  RIRExprCopyRef& incPart() { return part(2); }
  RIRStmtCopyRef& body() { return _body; }

  RIRLoopStmt* initForEnough(const RIRExprCopyRef& min = new RIRLitExpr(jalib::XToString(FORENOUGH_MIN_ITERS)),
                             const RIRExprCopyRef& max = new RIRLitExpr(jalib::XToString(FORENOUGH_MAX_ITERS)))
  {
    addAnnotation("for_enough");
    addExpr(new RIRNilExpr());
    addExpr(new RIRNilExpr());
    addExpr(new RIRNilExpr());
    addExpr(min);
    addExpr(max);
    return this;
  }
  
  ///Get the name of the variable limiting the iteration of the loop (if any)
  std::string getLimit ();
  
  ///Get the name of the induction variable of the loop
  std::string getInductionVariable() {  if( ! isCacheValid()) {
                                          computeInductionVariable();
                                        }
                                        return _inductionVariable;
                                     }
  
  ///Get the direction of the iteration
  /// "+" if the induction variable is increased
  /// "-" if the induction variable is decreased
  char getIterationDirection() {  if( ! isCacheValid()) {
                                    computeInductionVariable();
                                  }
                                  return _iterationDirection; 
                               }
                               
  std::string getInductionIncrement() { if( ! isCacheValid()) {
                                          computeInductionVariable();
                                        }
                                        return _inductionIncrement;
                                      }
  
  ///Make the loop increment part empty
  void clearIncPart() { 
    invalidateCache();
    incPart() = new RIRNilExpr(); 
  }
  
  ///Make the loop initialization part empty
  void clearDeclPart() { 
    invalidateCache();
    declPart() = new RIRNilExpr(); 
  }
  
  virtual unsigned int opsNumber() const {
    return declPart()->opsNumber() +
           testPart()->opsNumber() +
           incPart()->opsNumber() +
           body()->opsNumber();
  }
 
  virtual unsigned int subnodeCount(Type kind) const {
                                        unsigned int count = 0;
                                        if (type() == kind) {
                                          count++;
                                        }
                                        count += declPart()->subnodeCount(kind);
                                        count += testPart()->subnodeCount(kind);
                                        count += incPart()->subnodeCount(kind);
                                        count += body()->subnodeCount(kind);
                                       
                                       return count;
                                      }
  
private: //Methods
  ///Compute the induction variable. Also, store the iteration direction and the
  ///induction increment expression
  void computeInductionVariable();
  
  void computeInductionVariableFromIncrement() {
                              computeInductionVariableFromIncrement(incPart());
                            }
  
  void computeInductionVariableFromIncrement(RIRExprCopyRef increment);
  void computeInductionVariableFromBody();
  
  ///Are the cached attributes valid?
  bool isCacheValid() const { return _iterationDirection != '\0'; }
  
  ///Mark the cached attributes as invalid
  void invalidateCache() { _iterationDirection = '\0'; }
  
private:
  RIRStmtCopyRef _body;
  
  //Cached attributes
  std::string _inductionVariable;
  char _iterationDirection;
  std::string _inductionIncrement;
};

class RIRSwitchStmt: public RIRControlStmt{
public:
  RIRSwitchStmt(const RIRStmtCopyRef& p) : RIRControlStmt(STMT_SWITCH) { _body=p; }
  void print(std::ostream& o, RIRVisitor* printVisitor);
  void accept(RIRVisitor&);
  RIRSwitchStmt* clone() const;
  bool containsLeaf(const char* val) const{
    return RIRStmt::containsLeaf(val)
        || _body->containsLeaf(val);
  }
  
  virtual unsigned int subnodeCount(Type kind) const {
                return RIRStmt::subnodeCount(kind) + _body->subnodeCount(kind);
              }
              
private:
  RIRStmtCopyRef _body;
};

class RIRIfStmt: public RIRControlStmt{
public:
  RIRIfStmt(const RIRStmtCopyRef& t, const RIRStmtCopyRef& e=0) 
    :RIRControlStmt(STMT_COND)
    ,  _then(t)
    , _else(e) 
  {}
  void print(std::ostream& o, RIRVisitor* printVisitor);
  void accept(RIRVisitor&);
  RIRIfStmt* clone() const;
  bool containsLeaf(const char* val) const{
    return RIRStmt::containsLeaf(val)
        || _then->containsLeaf(val)
        ||(_else &&  _else->containsLeaf(val));
  }
  const RIRExprCopyRef& condPart() const { return _exprs.front(); }
  const RIRStmtCopyRef& thenPart() const { return _then; }
  const RIRStmtCopyRef& elsePart() const { return _else; }
  
  virtual unsigned int subnodeCount(Type kind) const {
                                        unsigned int count = 0;
                                        if (type() == kind) {
                                          count++;
                                        }
                                        count += condPart()->subnodeCount(kind);
                                        count += thenPart()->subnodeCount(kind);
                                        if (elsePart()) {
                                          count += elsePart()->subnodeCount(kind);
                                        }
                                        return count;
                                      }
private:
  RIRStmtCopyRef _then;
  RIRStmtCopyRef _else;
};

typedef RIRBasicStmt   RIRReturnStmt;
typedef RIRBasicStmt   RIRCaseStmt;
typedef RIRBasicStmt   RIRBreakStmt;
typedef RIRBasicStmt   RIRContinueStmt;
typedef RIRControlStmt RIRInlineConditional;

class RIRBlockStmt  : public RIRStmt {
public:
  RIRBlockStmt(const RIRBlockCopyRef& p) : RIRStmt(STMT_BLOCK) { _block=p; }
  void print(std::ostream& o, RIRVisitor* printVisitor);
  void accept(RIRVisitor&);
  RIRBlockStmt* clone() const;
  bool containsLeaf(const char* val) const;
  const RIRBlockCopyRef& extractBlock() const { return _block; }
  virtual unsigned int subnodeCount(Type kind) const;
private:
  RIRBlockCopyRef _block;
};

class RIRRawStmt  : public RIRStmt {
public:
  RIRRawStmt(const std::string& txt) : RIRStmt(STMT_RAW) { _src=txt; }
  void print(std::ostream& o, RIRVisitor* printVisitor);
  void accept(RIRVisitor&);
  RIRRawStmt* clone() const;
private:
  std::string _src;
};

/**
 * Rule IR Basic Block
 */
class RIRBlock : public RIRNode {
public:
  static RIRBlockCopyRef parse(const std::string& str, const jalib::SrcPosTaggable*);

  RIRBlock() : RIRNode(BLOCK) {}
  void addStmt(const RIRStmtCopyRef& p) { _stmts.push_back(p); }
  void print(std::ostream& o, RIRVisitor* printVisitor);
  void accept(RIRVisitor&);
  RIRBlock* clone() const;
  bool containsLeaf(const char* val) const{
    for(RIRStmtList::const_iterator i=_stmts.begin(); i!=_stmts.end(); ++i)
      if((*i)->containsLeaf(val))
        return true;
    return false;
  }

  const RIRStmtList& stmts() const { return _stmts; }
  
  virtual unsigned int subnodeCount(Type kind) const {
    unsigned int count = 0;
    if (type() == kind) {
      count++;
    }
    for (RIRStmtList::const_iterator i=_stmts.begin(),
                                     e=_stmts.end();
         i != e;
         ++i) {
      count += (*i)->subnodeCount(kind);   
    }
    
    return count;
  }
  
private:
  RIRStmtList _stmts;
};


}

#endif
