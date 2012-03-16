#!/usr/bin/python
"""This program verifies the effectiveness of the heuristic learning process by
running a set of training programs and, after each of them, running a test
program.
The run of the test program is timed and a plot of the times is generated"""

import learningcompiler
import learningframework
import os
import sys
import pbutil
import subprocess
import heuristicdb
import logging
import mylogger

from optparse import OptionParser

CONF_TIMEOUT = 5 * 60
STATIC_INPUT_PREFIX = "test"
HEURISTIC_KINDS = ["UserRule_blockNumber",
                   "UnrollingOptimizer_unrollingNumber",
                   "GCCPARAM_max-inline-insns-auto",
                   "GCCPARAM_max-inline-insns-single",
                   "GCCPARAM_large-function-insns",
                   "GCCPARAM_large-function-growth",
                   "GCCPARAM_large-unit-insns",
                   "GCCPARAM_inline-unit-growth",
                   "GCCPARAM_max-unroll-times",
                   "GCCPARAM_max-unrolled-insns"]
MAX_PRINTED_HEURISTICS = 10

logger = logging.getLogger(__name__)


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
    parser.add_option("--errorfile",
                      type="string",
                      help="file containing the log of errors",
                      default="error-log.dat")
    parser.add_option("--maxtuningsize",
                      type="int",
                      help="maximum size of the input to be used tuning a candidate",
                      default=None)
    parser.add_option("--maxtuningtime",
                      type="int",
                      help="maximum time (in seconds) to be spent tuning a candidate",
                      default=None)
    parser.add_option("--threads",
                      type="int",
                      help="maximum number of threads to be used for each test",
                      default=None)
    parser.add_option("--usemapreduce",
                      help=("Use the mincemeat.py library to distribute the "
                            "computation with a mapreduce approach"),
                      action="store_true", 
                      dest="usemapreduce", 
                      default=False)
    parser.add_option("--mintrialnumber",
                      type="int",
                      help=("minimum number of heuristics to generate for the "
                            "learning process"),
                      default=None)
    parser.add_option("--knowledge",
                      type="string",
                      help=("file containing the long-term learning knowledge "
                            "base"),
                      default=None)
                              
    return parser.parse_args()


class TestRunner(object):
    """Tests the effects of learning, by compiling benchmarks using the given
learningcompiler with learning disabled, then executing them and fetching 
the average timing result."""
    def __init__(self, learningcompiler, maxtestsize, maxtesttime):
        self._compiler = learningcompiler
        self._maxtestsize = maxtestsize
        self._maxtesttime = maxtesttime
        
    def test(self, src, outputbinary, staticInputName = None, 
             generateStaticInput = False):
        """Perform the test on the src program, generating the outputbinary.
If staticInputName is specified, such input is used. If generateStaticInput is 
True, than it is also generated"""
        timingruns = 5
        
        oldtuningsize = self._compiler.maxtuningsize
        oldtuningtime = self._compiler.maxtuningtime
        self._compiler.maxtuningsize = self._maxtestsize
        self._compiler.maxtuningtime = self._maxtesttime
        
        self._compiler.compileProgram(src, outputbinary, learn = False)
        
        self._compiler.maxtuningsize = oldtuningsize
        self._compiler.maxtuningtime = oldtuningtime

        if generateStaticInput:
            if not staticInputName:
                raise IOError
            cmd=[outputbinary, 
                 "--n=%s" % self._maxtestsize, 
                 "--iogen-create=%s" % staticInputName]
        
            print "Generating input files for the test program"
            NULL=open("/dev/null","w")
            logger.debug("Executing: %s" % cmd)
            p=subprocess.Popen(cmd, stdout=NULL, stderr=NULL)
            p.wait()
            NULL.close()
        
        if staticInputName:
            iogen_run = staticInputName
            size = None
        else:
            iogen_run = None
            size = self._maxtestsize
        
        res=pbutil.executeTimingRun(outputbinary, n=size, trials=timingruns, 
                                    iogen_run=iogen_run)
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
      self._initScript(kind)

  def _dataFileName(self, heuristicKind):
    return heuristicKind + ".dat"

  def _initScript(self, heuristicKind):
    script = open(heuristicKind+".gnuplot", "w")

    script.write("set xtics rotate by -90\n")
    script.write("set key outside\n")
    script.write("""set xtics out font "Arial,8"\n""")

    #Plot something random to force gnuplot to use the new settings
    #It will be overwritten by the real plot
    script.write("plot x\n")

    self._script[heuristicKind] = script


  def _finalizeScript(self, heuristicKind):
    script = self._script[heuristicKind]

    script.write("\n")
    script.close()


  def _plotFirstDataColumn(self, kind, heuristic):
    datafile = self._dataFileName(kind)
    title = heuristic
    initialplotcmd= """plot "%s" using 2:xticlabels(1) """ \
                    "with lines notitle, \\\n" \
                    """     "%s" using 2:xticlabels(1) title "%s" """ 
    initialplotcmd = initialplotcmd % (datafile, datafile, title)
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
      plotcmd=""", \\\n     "%s" using %d:xticlabels(1) with lines notitle """ \
              """, \\\n     "%s" using %d:xticlabels(1) title "%s" """
      plotcmd = plotcmd % (datafile, column, datafile, column, title)
      script.write(plotcmd)

    script.flush()



  def outputLineByKind(self, programName, heuristicKind):
    outFile = self._out[heuristicKind]
    heurList = self._heurList[heuristicKind]

    outFile.write(programName)

    scores = self._db.getHeuristicsScoreByKind(heuristicKind, 
                                                    MAX_PRINTED_HEURISTICS)

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
  examples_path= os.path.join(petabricks_path, "examples")  
  pbc = os.path.join(petabricks_path,"src/pbc")

  (options, args) = parseCmdline(petabricks_path)

  if len(args)==0:
    print "No test program specified"
    exit(-1)

  mylogger.configureLogging(options.errorfile)

  testProgram=os.path.abspath(args[0])
  testBinary = os.path.splitext(testProgram)[0]

  #Create objects
  compiler = learningcompiler.LearningCompiler(pbc,
                                        heuristicSetFileName=options.heuristics,
                                        n=options.maxtuningsize,
                                        maxTuningTime=options.maxtuningtime,
                                        threads=options.threads,
                                        use_mapreduce=options.usemapreduce,
                                        min_trial_number=options.mintrialnumber,
                                        knowledge=options.knowledge)
  tester = TestRunner(compiler, options.maxtestsize, options.maxtesttime)  
  hgdatagen = HeuristicsGraphDataGenerator(HEURISTIC_KINDS)

  #Open files
  trainingset = open(options.trainingset, "r")
  resultfile = open(options.resultfile, "w")


  print "Compiling and testing the initial version of the test program"
  try:
      res = tester.test(testProgram, testBinary, 
                  STATIC_INPUT_PREFIX, generateStaticInput=True)
  except:
      logger.exception("ERROR compiling and testing the test program:\n")
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
        compiler.compileProgram(src, binary)
        
        print "Compiling and testing the test program"
        res = tester.test(testProgram, testBinary, 
                          STATIC_INPUT_PREFIX)
    except pbutil.TimingRunTimeout:
        logger.exception("Timeout!")
        res = options.maxtesttime
    except learningframework.AllCandidatesCrashError:
        logger.error("All candidates crash while compiling: %s", trainingprogram)
        res=-1
    except:
        logger.exception("Irrecoverable error while learning:\n")
        res=-1
        sys.exit(-2)

    resultfile.write(""""%s" %f\n""" % (trainingprogram, res))
    resultfile.flush()

    hgdatagen.outputLine(trainingprogram)

  print "Results written to " + options.resultfile

  hgdatagen.close()
  compiler.close()

if __name__ == "__main__":
    main()
