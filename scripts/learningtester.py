#!/usr/bin/python
"""This program verifies the effectiveness of the heuristic learning process by
running a set of training programs and, after each of them, running a test 
program.
The run of the test program is timed and a plot of the times is generated"""

import learningcompiler
import os
import sys
import pbutil
import sgatuner
import traceback
import subprocess
from pbutil_support import compileBenchmark
from optparse import OptionParser

CONF_TIMEOUT=5*60
STATIC_INPUT_PREFIX="test"

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
  parser.add_option("--maxtestsize",
                    type="int",
                    help="size of the input to generate for testing",
                    default=256)
  parser.add_option("--maxtesttime",
	    type="int",
	    help="maximum time (in seconds) to be spent tuning the test program",
	    default=CONF_TIMEOUT)
  parser.add_option("--resultfile",
		type="string",
		help="file containing the results in gnuplot-compatible format",
		default="training-results.dat")
  parser.add_option("--maxtuningsize",
		type="int",
		help="maximum size of the input to be used tuning a candidate",
		default=None)
  parser.add_option("--maxtuningtime",
		type="int",
		help="maximum time (in seconds) to be spent tuning a candidate",
		default=None)
		    
  return parser.parse_args()



def testLearning(pbc, testProgram, testBinary, n, maxtime=CONF_TIMEOUT, staticInputName=None, generateStaticInput=False):
  """Tests the effects of learning, by compiling the benchmark with the current
best heuristics, then executing it and fetching the average timing result

If staticInputName is specified, such input is used. If generateStaticInput is True, than it is also generated"""
  compileBenchmark(pbc, testProgram, testBinary, timeout=CONF_TIMEOUT)
  
  candidates=[]
  sgatuner.autotune_withparams(testBinary, candidates, n, maxtime)
  
  if generateStaticInput:
    if not staticInputName:
      raise IOError
    cmd=[testBinary, "--n=%s"%n, "--iogen-create=%s"%staticInputName]
    
    print "Generating input files for the test program"
    NULL=open("/dev/null","w")
    p=subprocess.Popen(cmd, stdout=NULL, stderr=NULL)
    p.wait()
    NULL.close()

  if staticInputName:
    iogen_run=staticInputName
    size=None
  else:
    iogen_run=None
    size=n
    
  res=pbutil.executeTimingRun(testBinary, n=size, trials=None, iogen_run=iogen_run)
  avgExecutionTime=res["average"]
  
  return avgExecutionTime
  
  

  
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
                                      heuristicSetFileName = options.heuristics,
                                      n=options.maxtuningsize, 
                                      maxTuningTime=options.maxtuningtime)
  
  examples_path= os.path.join(petabricks_path, "examples")
  
  trainingset = open(options.trainingset, "r")
  resultfile = open(options.resultfile, "w")
  
  print "Compiling and testing the initial version of the test program"
  try:
    res = testLearning(pbc, 
		       testProgram, 
		       testBinary, 
		       options.maxtestsize, 
		       options.maxtesttime,
		       STATIC_INPUT_PREFIX,
		       generateStaticInput=True)
  except:
    sys.stderr.write("ERROR compiling and testing the test program:\n")
    einfo = sys.exc_info()
    print einfo[0]
    print einfo[1]
    traceback.print_tb(einfo[2])
    res = CONF_TIMEOUT
    sys.exit(-1)
  
  resultfile.write(""""INITIAL" %s\n""" % res)
  
  for line in trainingset:
    trainingprogram=line.strip(" \n\t")
    if len(trainingprogram)==0 or trainingprogram[0]=="#":
      #Comment or empty line
      continue
    
    program=os.path.join(examples_path, trainingprogram)
    src=program+".pbcc"
    binary=program
    
    print "Learning from "+trainingprogram
    
    try:
      compiler.compileLearningHeuristics(src, binary)
      print "Compiling and testing the test program"
      res=testLearning(pbc, 
		       testProgram, 
		       testBinary, 
		       options.maxtestsize, 
		       options.maxtesttime,
		       STATIC_INPUT_PREFIX)
    except pbutil.TimingRunTimeout:
      res = CONF_TIMEOUT
    except:
      sys.stderr.write("Irrecoverable error while learning:\n")
      einfo = sys.exc_info()
      print einfo[0]
      print einfo[1]
      traceback.print_tb(einfo[2])
      res=-1

    resultfile.write(""""%s" %f\n""" % (trainingprogram, res))
    resultfile.flush()

  print "Results written to " + options.resultfile


  
if __name__ == "__main__":
  main()
