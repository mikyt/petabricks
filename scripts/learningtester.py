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
import heuristicdb
from pbutil_support import compileBenchmark
from optparse import OptionParser

CONF_TIMEOUT=5*60
STATIC_INPUT_PREFIX="test"
HEURISTIC_KINDS = ["UserRule_blockNumber", "UnrollingOptimizer_unrollingNumber"]

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
  

class HeuristicsGraphDataGenerator(object):
  def __init__(self, heuristicKinds):
    self._db = heuristicdb.HeuristicDB()
    self._heuristicKinds = heuristicKinds
    
    #Output files (one for each heuristic kind)
    self._out = {}
    
    #Graph generation scripts (one for each heuristic kind)
    self._script = {}
    
    #Ordered lists of heuristics (one for each kind)
    self._heurList = {}
    
    for kind in self._heuristicKinds:
      self._heurList[kind] = []
      datafile = self._dataFileName(kind)
      self._out[kind] = open(datafile, "w")
      self._script[kind] = self._initScript(kind)
  
  def _dataFileName(self, heuristicKind):
    return heuristicKind + ".dat"
  
  def _initScript(self, heuristicKind):
    script = open(heuristicKind+".gnuplot", "w")
    script.write("set xtics rotate by 90\n")
    script.write("set key outside\n")
    return script
    
  def _finalizeScript(self, heuristicKind):
    script = self._script[heuristicKind]
    
    script.write("\n")
    script.close()
    
    
  def _plotFirstDataColumn(self, kind, heuristic):
    datafile = self._dataFileName(kind)
    title = heuristic
    initialplotcmd="""plot "%s" using 2:xticlabels(1) smooth csplines title "%s" """ % (datafile, title)
    self._script[kind].write(initialplotcmd)
    
    
  def _updateScript(self, heuristicKind, newHeurList):
    """Update the generation script with the lines needed to plot 
    the new heuristics"""
    if len(newHeurList)==0:
      #Nothing to be done
      return
    
    lastPlottedColumn = len(self._heurList[heuristicKind])+1
    
    if lastPlottedColumn==1:
      self._plotFirstDataColumn(heuristicKind, newHeurList[0])
      column = 2
      toBePlotted = newHeurList[1:]
    else:
      column = lastPlottedColumn
      toBePlotted = newHeurList
    
    #Plot every other column
    datafile = self._dataFileName(heuristicKind)
    script = self._script[heuristicKind]
    for heur in toBePlotted:
      column = column + 1
      title = heur
      plotcmd=""", \\\n     "%s" using %d:xticlabels(1) smooth csplines title "%s" """ % (datafile, column, title)
      script.write(plotcmd)
      
    script.flush()

    
    
  def outputLineByKind(self, programName, heuristicKind):
    outFile = self._out[heuristicKind]
    heurList = self._heurList[heuristicKind]
    
    outFile.write(programName)
    
    scores = self._db.getHeuristicsFinalScoreByKind(heuristicKind)
    
    #Add new heuristics to the list keeping the order of the previous ones
    keys = scores.keys()
    newHeurList = filter(lambda x: x not in heurList, keys)
    
    self._updateScript(heuristicKind, newHeurList)
    heurList.extend(newHeurList)
    
    #Output the line
    for heuristic in heurList:
      outFile.write("\t")
      try:
	outFile.write(str(scores[heuristic]))
      except KeyError:
	#No score available for the current heuristic at this time
	outFile.write("-")
    
    outFile.write("\n")
    outFile.flush()
    
  
  def outputLine(self, programName):
    """Outputs one line for each heuristic kind file"""
    for kind in self._heuristicKinds:
      self.outputLineByKind(programName, kind)
      
    
  def close(self):
    self._db.close()
    for kind in self._heuristicKinds:
      self._out[kind].close()
      self._finalizeScript(kind)
      
    
    
  
  
  
  
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
  
  #Create objects
  compiler = learningcompiler.LearningCompiler(pbc, 
                                      heuristicSetFileName = options.heuristics,
                                      n=options.maxtuningsize, 
                                      maxTuningTime=options.maxtuningtime)
  
  hgdatagen = HeuristicsGraphDataGenerator(HEURISTIC_KINDS)
  
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
  
  hgdatagen.outputLine("INITIAL")
  
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
    
    hgdatagen.outputLine(trainingprogram)

  print "Results written to " + options.resultfile
  
  hgdatagen.close()
  
if __name__ == "__main__":
  main()
