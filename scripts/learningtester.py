#!/usr/bin/python
"""This program verifies the effectiveness of the heuristic learning process by
running a set of training programs and, after each of them, running a test 
program.
The run of the test program is timed and a plot of the times is generated"""

import learningcompiler
import os
import sys
import pbutil
from pbutil_support import compileBenchmark
from optparse import OptionParser

CONF_TIMEOUT=5*60

def parseCmdline(petabricks_path):
  parser = OptionParser(usage="usage: learningtester.py [options]")
  parser.add_option("--heuristics", 
                type="string", 
                help="name of the file containing the set of heuristics to use", 
                default=None)
  parser.add_option("--trainingset",    
          type="string", 
          help="name of the file containing the list of programs to learn from", 
          default=os.path.join(petabricks_path, "scripts/trainingset.txt"))
  parser.add_option("-n",
                    type="int",
                    help="size of the input to generate for testing",
                    default=256)
  parser.add_option("--trials",
		    type="int",
		    help="number of executions of the test program for averaging the result",
		    default=1)
  return parser.parse_args()



def testLearning(pbc, testProgram, testBinary, n, trials):
  compileBenchmark(pbc, testProgram, testBinary, timeout=CONF_TIMEOUT)
  
  res=pbutil.executeTimingRun(testBinary, n, args=[], limit=CONF_TIMEOUT, trials=trials)
  avg=res["average"]
  
  return avg
  
  
  
  
def main():
  """The body of the program"""
  script_path = sys.path[0]
  petabricks_path = os.path.join(script_path, "../")
  petabricks_path = os.path.normpath(petabricks_path)

  pbc = os.path.join(petabricks_path,"src/pbc")
  
  (options, args) = parseCmdline(petabricks_path)
  
  testProgram=os.path.abspath(args[0])
  testBinary = os.path.splitext(testProgram)[0]
  
  compiler = learningcompiler.LearningCompiler(pbc, 
                                      heuristicSetFileName = options.heuristics)
  
  examples_path= os.path.join(petabricks_path, "examples")
  
  results=[]
  
  print "Compiling and testing the initial version of the test program"
  results.append(("INITIAL", testLearning(pbc, testProgram, testBinary, options.n, options.trials)))
  
  trainingset = open(options.trainingset, "r")
  for line in trainingset:
    trainingprogram=line.strip(" \n")
    program=os.path.join(examples_path, trainingprogram)
    src=program+".pbcc"
    binary=program
    
    print "Learning from "+trainingprogram
    print "Src: "+src
    print "binary: "+binary
    compiler.compileLearningHeuristics(src, binary)
    
    print "Compiling and testing the test program"
    res=testLearning(pbc, testProgram, testBinary, options.n, options.trials)
    
    results.append((trainingprogram, res))

  print results
  
  
if __name__ == "__main__":
  main()