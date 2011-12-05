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
  parser = OptionParser(usage="usage: learningtester.py [options] testprogram")
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
  parser.add_option("--resultfile",
		    type="string",
		    help="file containing the results in gnuplot-compatible format",
		    default="training-results.dat")
		    
  return parser.parse_args()



def testLearning(pbc, testProgram, testBinary, n, trials):
  """Tests the effects of learning, by compiling the benchmark with the current
best heuristics, then executing it and fetching the average timing result"""
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
  
  if len(args)==0:
    print "No test program specified"
    exit(-1)
  
  testProgram=os.path.abspath(args[0])
  testBinary = os.path.splitext(testProgram)[0]
  
  compiler = learningcompiler.LearningCompiler(pbc, 
                                      heuristicSetFileName = options.heuristics)
  
  examples_path= os.path.join(petabricks_path, "examples")
  
  trainingset = open(options.trainingset, "r")
  resultfile = open(options.resultfile, "w")
  
  print "Compiling and testing the initial version of the test program"
  resultfile.write(""""INITIAL" %s\n""" % testLearning(pbc, testProgram, testBinary, options.n, options.trials))
  
  for line in trainingset:
    trainingprogram=line.strip(" \n\t")
    if trainingprogram[0]=="#":
      #Comment
      continue
    
    program=os.path.join(examples_path, trainingprogram)
    src=program+".pbcc"
    binary=program
    
    print "Learning from "+trainingprogram
    
    try:
      compiler.compileLearningHeuristics(src, binary)
      print "Compiling and testing the test program"
      res=testLearning(pbc, testProgram, testBinary, options.n, options.trials)
    except Exception as e:
      sys.stderr.write("Irrecoverable error while learning:\n")
      print e

      res=-1

    resultfile.write(""""%s" %f\n""" % (trainingprogram, res))
    resultfile.flush()

  print "Results written to " + options.resultfile


  
if __name__ == "__main__":
  main()
