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

#include "unrollingoptimizer.h"

void petabricks::UnrollingOptimizer::setUnrolledLoopCondition(RIRLoopStmt& loop, int unrollingNumber) {
  std::string inductionVar = loop.getInductionVariable();
  std::string limit = loop.getLimit();
  char direction = loop.getIterationDirection();
  
  RIRExprCopyRef& condition = loop.testPart();

  std::string comparisonOP;
  if(direction == '+') {
    comparisonOP = "<";
  }
  else {
    //Direction == '-'
    comparisonOP = ">=";
  }
  
  std::string newCondStr = inductionVar + direction + jalib::XToString(unrollingNumber) + comparisonOP + limit ;
  JTRACE("New Loop Condition")(newCondStr);
  RIRExprCopyRef newCond = RIRExpr::parse(newCondStr, SRCPOS());
    
  //Substitute the condition in the loop
  condition = newCond;
}



void petabricks::UnrollingOptimizer::setUnrolledLoopBody(RIRLoopStmt& loop, int unrollingNumber) {
  RIRStmtCopyRef& loopBody = loop.body();
  
  RIRBlockCopyRef newBody = new RIRBlock();
  
  bool isIncrementAlreadyInBody = (loop.incPart()->partsNumber() == 0);
  
  for(int i=0; i<unrollingNumber; ++i) {
    newBody->addStmt(loopBody);
    
    if( ! isIncrementAlreadyInBody) {
      //Insert increment instruction in the loop body
      RIRStmtCopyRef increment= new RIRBasicStmt();
      JTRACE("InductionIncrement")(loop.getInductionIncrement());
      increment->addExpr(RIRExpr::parse(loop.getInductionIncrement(), SRCPOS()));
      newBody->addStmt(increment);
    }
  }

  loopBody = new RIRBlockStmt(newBody);
}



bool petabricks::UnrollingOptimizer::shouldUnroll(RIRLoopStmt& loop) {
  RIRExprCopyRef& loopCondition = loop.testPart();
  
  if(loopCondition->containsBoolOp() || loopCondition->containsTernaryOp()) {
    JWARNING(false && "Are we sure this cannot be unrolled?")(loopCondition);
    return false;
  }
  
  std::string inductionVar = loop.getInductionVariable();
  
  if(loopCondition->isComparison()) {
    std::string compOp = loopCondition->getComparisonOp();
    RIRExprCopyRef LHS = loopCondition->getLHS(compOp);
    RIRExprCopyRef RHS = loopCondition->getRHS(compOp);
    
    if(LHS->toString() == inductionVar || RHS->toString() == inductionVar) {
      //It's a direct comparison with the induction variable. Let's unroll!
      return true;
    }
  }
    
  JWARNING(false && "Are we sure this cannot be unrolled?")(loopCondition);
  return false;
}


void petabricks::UnrollingOptimizer::after(RIRStmtCopyRef& stmt) {
  RIRNode::Type type = stmt->type();

  if(type != RIRNode::STMT_LOOP) {
    //Not a loop: no unrolling
    return;
  }
  
  RIRLoopStmt& loop = (RIRLoopStmt&) *stmt;

  if ( ! shouldUnroll(loop)) {
    return;
  }
  
  std::string limit = loop.getLimit();
  if(limit=="") {
    //Unable to determine the limit of the loop: do nothing
    return;
  }
  
  ValueMap features;
  features["loopNestingLevel"] = getLoopNestingLevel(*this);
  features["loopBodySize"] = getLoopBodySize(*this);
  features["loopBodyOps"] = getLoopBodyOps(*this);
  HeuristicPtr& unrollingHeur = HeuristicManager::instance().getHeuristic("UnrollingOptimizer_unrollingNumber");
  int unrollingNumber =unrollingHeur->eval(features);
  
  if (unrollingNumber < 2) {
    //The best unrolling is no unrolling: nothing to do!
    return;
  }
  
  if(loop.hasAnnotation("justUnrolled")) {
    //This is the result of a previous unrolling.
    //It doesn't make sense to unroll it again right now
    
    //But maybe in the future...
    stmt->removeAnnotation("justUnrolled");
    return;
  }
  
  /* Create a new block to contain the unrolled loop and the finishing one */
  RIRBlockCopyRef newBlock = new RIRBlock();
  
  if (loop.declPart()->partsNumber() != 0) {
    /* Extract the declaration part from the original loop*/
    RIRStmt* declStmt = new RIRBasicStmt();
    declStmt->addExpr(loop.declPart());
    loop.clearDeclPart();

    newBlock->addStmt(declStmt);
  }
  
  /* Get a copy of the original loop */
  RIRLoopStmt* finishingLoop = loop.clone();
  
  /* Unroll the current loop */
  setUnrolledLoopCondition(loop, unrollingNumber);
  setUnrolledLoopBody(loop, unrollingNumber);
  loop.clearIncPart();
  loop.addAnnotation("justUnrolled");
  newBlock->addStmt(&loop);
  
  /* Setup the finishing loop */
  finishingLoop->clearDeclPart();
  finishingLoop->addAnnotation("justUnrolled");
  newBlock->addStmt(finishingLoop);
  
  stmt = new RIRBlockStmt(newBlock);
}

/*******************************************************************
 * Features
 *******************************************************************/
double petabricks::UnrollingOptimizer::getLoopNestingLevel(const RIRCompilerPass& context) {
  RIRNodeRef currentNode = context.currentNode();
  double loopNestingLevel = 0;
  while (currentNode) {
    if(currentNode->type() == RIRNode::STMT_LOOP) {
      loopNestingLevel++;
    }
    currentNode = context.parentNode(currentNode);
  }
  
  return loopNestingLevel;
}



double petabricks::UnrollingOptimizer::getLoopBodySize(const RIRCompilerPass& context) {
  //Counts the number of statements.
  RIRNodeRef currentNode = context.currentNode();
  
  //Find the beginning of the current loop
  while (currentNode && currentNode->type() != RIRNode::STMT_LOOP) {
    currentNode = context.parentNode(currentNode);
  }
  
  if ( ! currentNode) {
    //We are not inside a loop
    return 0;
  }
  
  RIRLoopStmt& loop = (RIRLoopStmt&) *currentNode;
  RIRStmtCopyRef& body = loop.body();
  const RIRBlockCopyRef& block = body->extractBlock();
  return block->stmts().size();
}



double petabricks::UnrollingOptimizer::getLoopBodyOps(const RIRCompilerPass& context) {
  RIRNodeRef currentNode = context.currentNode();
  
  //Find the beginning of the current loop
  while (currentNode && currentNode->type() != RIRNode::STMT_LOOP) {
    currentNode = context.parentNode(currentNode);
  }
  
  if ( ! currentNode) {
    //We are not inside a loop
    return 0;
  }
  
  RIRLoopStmt& loop = (RIRLoopStmt&) *currentNode;
  
  return loop.opsNumber();
}