#!/usr/bin/python
"""This program verifies the effectiveness of the heuristic learning process by
running a set of training programs and, after each of them, running a test
program.
The run of the test program is timed and a plot of the times is generated"""

import learninggcc
import os
import sys
import heuristicdb
import logging
import mylogger

from optparse import OptionParser

CONF_TIMEOUT = 5 * 60
STATIC_INPUT_PREFIX = "test"
HEURISTIC_KINDS = ["-funroll-loops", "-fweb", "-O", "UseOFlag"]
MAX_PRINTED_HEURISTICS = 10
NUM_GENERATIONS = 3

logger = logging.getLogger(__name__)


def parseCmdline():
    parser = OptionParser(usage="usage: learninggcctester.py [options] testprogram")
    parser.add_option("--trainingset",
                      type="string",
                      help="name of the file containing the list of programs to learn from",
                      default="trainingset.txt")
    parser.add_option("--resultfile",
                      type="string",
                      help="file containing the results in gnuplot-compatible format",
                      default="training-results.dat")
    parser.add_option("--logfile",
                      type="string",
                      help="file containing the log of errors",
                      default="log.dat")
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
                      default=8)
    parser.add_option("--knowledge",
                      type="string",
                      help=("file containing the long-term learning knowledge "
                            "base"),
                      default=None)
    parser.add_option("--generations",
                      type="int",
                      help=("number of generations to be used for the learning "
                            "process (default %d)") % NUM_GENERATIONS,
                      default=NUM_GENERATIONS)
    return parser.parse_args()


class TestRunner(object):
    """Tests the effects of learning, by compiling benchmarks using the given
learningcompiler with learning disabled, then executing them and fetching 
the average timing result."""
    def __init__(self, learningcompiler):
        self._compiler = learningcompiler
        
    def test(self, benchmark):
        """Perform the test on the src program, generating the outputbinary.
If staticInputName is specified, such input is used. If generateStaticInput is 
True, than it is also generated"""        
        res = self._compiler.compileProgram(benchmark, learn = False)
        if res != 0:
            logger.error("Error compiling the program: %s", benchmark)
            sys.exit(res)
        
        timingfile = open(learninggcc.CONF_TIMING_FILE_NAME)
        res = float(timingfile.readline())
        timingfile.close()
        
        return res


class HeuristicsGraphDataGenerator(object):
  def __init__(self, heuristicKinds, knowledge=None):
    self._db = heuristicdb.HeuristicDB(knowledge)
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

  (options, args) = parseCmdline()

  if len(args)==0:
    print "No test program specified"
    exit(-1)

  mylogger.configureLogging(options.logfile)

  testProgram = os.path.abspath(args[0])
  
  #Create objects
  compiler = learninggcc.LearningGCC(use_mapreduce=options.usemapreduce,
                                     min_trial_number=options.mintrialnumber,
                                     knowledge=options.knowledge,
                                     generations=options.generations)
  tester = TestRunner(compiler)  
  hgdatagen = HeuristicsGraphDataGenerator(HEURISTIC_KINDS, options.knowledge)

  #Open files
  trainingset = open(options.trainingset, "r")
  resultfile = open(options.resultfile, "w")


  print "Compiling and testing the initial version of the test program"
  
  res = tester.test(testProgram)
  
  resultfile.write(""""INITIAL" %s\n""" % res)

  hgdatagen.outputLine("INITIAL")

  for line in trainingset:
    trainingprogram=line.strip(" \n\t")
    if len(trainingprogram)==0 or trainingprogram[0]=="#":
      #Comment or empty line
      continue

    print "Learning from "+trainingprogram


    res = compiler.compileProgram(trainingprogram)
    if res != 0:
        logger.error("Error compiling the program: %s", trainingprogram)
        sys.exit(-1)
    
    print "Compiling and testing the test program"
    res = tester.test(testProgram)


    resultfile.write(""""%s" %f\n""" % (trainingprogram, res))
    resultfile.flush()

    hgdatagen.outputLine(trainingprogram)

  print "Results written to " + options.resultfile

  hgdatagen.close()
  compiler.close()

if __name__ == "__main__":
    main()
