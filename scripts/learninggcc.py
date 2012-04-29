#!/usr/bin/python
"""Framework implementing long term learning of heuristics for the PetaBricks
compiler

Michele Tartara <mikyt@users.sourceforge.net>"""

import learningframework
import heuristic
import formula
import logging
import mylogger
import optparse
import os
import shutil
import subprocess
import sys

#------------------ Config --------------------
CONF_TIMING_TOOL = os.path.join(sys.path[0],"timer.py")
CONF_TIMING_FILE_NAME = "tmp_time"
CONF_DELETE_TEMP_DIR = True
CONF_GCC_PLUGIN = "/home/mikyt/programmi/staticcounter/staticcounter.so"
NUM_GENERATIONS=3
#CONF_TIMEOUT = 60*30
#CONF_HEURISTIC_FILE_NAME = "heuristics.txt"
#STATIC_INPUT_PREFIX = "learning_compiler_static"
#NUM_TIMING_TESTS = 5
#----------------------------------------------


logger = logging.getLogger(__name__)

class Error(Exception):
    """Base exception class for this module, inherited by all the other 
    exceptions"""
    pass

class CompilationError(Error):
    pass

class TimingRunError(Error):
    pass

class WrongHeuristicTypeError(Error):
    pass

class HeuristicEvaluationFailedError(Error):
    pass

def parseCmdline():
    parser = optparse.OptionParser(
        usage="usage: learninggcc.py [options] testprogram"
    )
#    parser.add_option("--heuristics",
#                      type="string",
#                      help="name of the file containing the set of heuristics to use",
#                      default=None)
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
    parser.add_option("--tmpdir",
                      type="string",
                      help=("directory used for the temporary files"),
                      default="/tmp/")
    parser.add_option("--generations",
                      type="int",
                      help=("number of generations to be used for the learning "
                            "process (default %d)") % NUM_GENERATIONS,
                      default=NUM_GENERATIONS)
    return parser.parse_args()
        
        
def compute_speedup(candidate, reference):
    speedup = reference / candidate
    return speedup


def compilebenchmark(programdir, gccflags=None):
    cmd = [os.path.join(programdir, "__compile"), "gcc"]
    
    gccpluginflag = "-fplugin="+CONF_GCC_PLUGIN
    
    if not gccflags:
        gccflags = ""
    
    all_gccflags = gccpluginflag + " " + gccflags

    env = dict(os.environ)
    env["CCC_OPTS"] = all_gccflags
        
    logger.debug("Executing: %s", " ".join(cmd))
    p = subprocess.Popen(cmd, cwd=programdir, env=env)
    retcode = p.wait()
    
    if retcode != 0:
        raise CompilationError(retcode)
        
def timingrun(programdir):
    cmd = [os.path.join(programdir, "__run"), "1"]
    
    env = dict(os.environ)
    env["CCC_RE"] = CONF_TIMING_TOOL
    
    logger.debug("Executing: %s", " ".join(cmd))
    p = subprocess.Popen(cmd, cwd=programdir, env=env)
    retcode = p.wait()

    if retcode != 0:
        raise TimingRunError(retcode)
    
    timingfilename = os.path.join(programdir, CONF_TIMING_FILE_NAME)
    timingfile = open(timingfilename)
    time = float(timingfile.readline())
    timingfile.close()
    return time

def copybenchmark(benchmark, destdir):
    srcdir = os.path.join(benchmark, "src")
    shutil.copytree(srcdir, destdir)
    
def hset_to_flag_string(hset, valuemap={}):
    flags = []
    for heuristic in hset.itervalues():
        flags.append(heuristic_to_flagstring(heuristic, valuemap))
    return " ".join(flags)

def heuristic_to_flagstring(heuristic, valuemap):
    heuristic.increase_uses()
    try:
        if heuristic.resulttype == formula.BooleanResult:
            return heuristic_bool_to_flagstring(heuristic, valuemap)
        elif heuristic.resulttype == formula.IntegerResult:
            return heuristic_int_to_flagstring(heuristic, valuemap)
        raise WrongHeuristicTypeError
    except ZeroDivisionError:
        raise HeuristicEvaluationFailedError(heuristic, valuemap)
        

def heuristic_bool_to_flagstring(heuristic, valuemap):
    useflag = heuristic.evaluate(valuemap)
    if useflag:
        return heuristic.name
    else:
        return "-fno-"+heuristic.name[2:]
    
def heuristic_int_to_flagstring(heuristic, valuemap):
    value = heuristic.evaluate(valuemap)
    
    if heuristic.min_val and value < heuristic.min_val:
        value = heuristic.min_val
        heuristic.increase_tooLow()
    elif heuristic.max_val and value > heuristic.max_val:
        value = heuristic.max_val
        heuristic.increase_tooHigh()
        

    if heuristic.name=="-O":
        return "-O"+str(value)

    return "%s=%d" % (heuristic.name, value)    
    
def test_heuristic_set(benchmark, count, hSet, additionalParameters):
    """Return the object representing a tested candidate, with (at least) the
following attributes:

  * failed (bool): has the candidate failed the compilation/testing process?
  * assignScores (bool): should the score be assigned to the candidate normally
                         or should we just mark it as used (thus penalizing it)
  * heuristicSet (HeuristicSet): the set of heuristics that generated the
                                 program"""
    candidate = None
    basesubdir = additionalParameters["basesubdir"]
    reference = additionalParameters["reference_performance"]
    valuemap = additionalParameters["valuemap"]
    dirnumber = count + 1    

    logger.info("Testing candidate %d", dirnumber)
    
    #Define more file names
    programdir = os.path.join(basesubdir, str(dirnumber)+".tmp")
    if os.path.isdir(programdir):
        #Create the output directory
        shutil.rmtree(programdir)

    copybenchmark(benchmark, programdir)
    
    hSet.prepare_for_usage_statistics()
    
    try:
        gccflags = hset_to_flag_string(hSet, valuemap)

        compilebenchmark(programdir, gccflags)
        
        execution_time = timingrun(programdir)

        candidate = learningframework.SuccessfulCandidate(hSet)
        candidate.executionTime = execution_time
        candidate.speedup = compute_speedup(execution_time, reference)

        return candidate
    except HeuristicEvaluationFailedError:
        candidate = learningframework.FailedCandidate(hSet, assignScores=True)
        return candidate
    except CompilationError:
        candidate = learningframework.FailedCandidate(hSet, assignScores=True)
        return candidate
    except TimingRunError:
        candidate = learningframework.FailedCandidate(hSet, assignScores=True)
        return candidate
 
    
    
class LearningGCC(learningframework.Learner):
  _testHSet = staticmethod(test_heuristic_set)
  
  def __init__(self, heuristicSetFileName=None, use_mapreduce=False, 
               min_trial_number=None, knowledge=None, tmpdir=None, 
               generations=NUM_GENERATIONS):
    super(LearningGCC, self).__init__(heuristicSetFileName, 
                                      use_mapreduce=use_mapreduce,
                                      min_trial_number=min_trial_number,
                                      knowledge=knowledge,
                                      generations=generations)
    self.min_trial_number = min_trial_number
    self.tmpdir = tmpdir

  def close(self):
       super(LearningGCC, self).close()
       
  @staticmethod
  def _candidateSortingKey(candidate):
      """Generates a comparison key for a candidate.
    Candidates are sorted by speedup wrt the reference candidate (compiled
    with default heuristics).
    The first candidate is the one with the bigger speedup"""
      if candidate.failed:
        return float('inf')
      return (1.0 / candidate.speedup)
  
  def compileProgram(self, benchmark, learn=True):
    return self.use_learning(benchmark, learn)
    

  def _setup(self, benchmark, additionalParameters):
    self._neededHeuristics = None
    self._availablefeatures = None
    
    #Define file names
    path, basename = os.path.split(benchmark)
    if path == "":
      path="./"
    basesubdir = os.path.abspath(benchmark)
    
    additionalParameters["basesubdir"] = basesubdir
    additionalParameters["basename"] = basename
    additionalParameters["path"] = path
    candidates = additionalParameters["candidates"]
    
    #Compile with default heuristics
    programdir= os.path.join(basesubdir, "0.tmp")
    if os.path.isdir(programdir):
      #Create the output directory
      shutil.rmtree(programdir)
    
    copybenchmark(benchmark, programdir)
    
    try: 
        hSet = heuristic.HeuristicSet()
        hSet["-O"] = (heuristic.Heuristic("-O", "0", formula.IntegerResult))
        
        hSet.prepare_for_usage_statistics()
        
        gccflags = hset_to_flag_string(hSet)

        compilebenchmark(programdir, gccflags)
        
        execution_time = timingrun(programdir)
        
        default_candidate = learningframework.SuccessfulCandidate(hSet)
        default_candidate.speedup = 1 #This is the reference for the speedup
        default_candidate.originalIndex = -1
        default_candidate.executionTime = execution_time
        
        candidates.append(default_candidate)
                
        #Store for later use by the candidates        
        additionalParameters["reference_performance"] = execution_time
            
        #Load features value map from file
        valuemap = heuristic.FeatureValueMap()
        xmlfilename = os.path.join(programdir, "features.xml")
        valuemap.importFromXml(xmlfilename)
        additionalParameters["valuemap"] = valuemap
        
        availablefeaturesnames = valuemap.keys()

        self._availablefeatures = heuristic.AvailableFeatures()

        for needed in self._getNeededHeuristics(benchmark):
            self._availablefeatures[needed.name].extend(availablefeaturesnames)
            
        
        return 0        
    except CompilationError:
        logger.exception("Default candidate compilation failed")
        return -1

  def _getNeededHeuristics(self, benchmark):
      if self._neededHeuristics:
          return self._neededHeuristics
          
      heurlist = []
    
      self._availablefeatures["-O"] = []
      h = heuristic.NeededHeuristic("-O", self._get_available_features(benchmark, "-O"), formula.IntegerResult, min_val=0, max_val=3)
      h.default_value = 0
      heurlist.append(h)

      script_path = sys.path[0]
      heuristicfile = os.path.join(script_path, "gccneededheuristics.inc")
      execfile(heuristicfile)
      
      self._neededHeuristics = heurlist
      return self._neededHeuristics


  def _get_available_features(self, unused_benchmark, heuristic_name=None):
      if heuristic_name is not None:
          return self._availablefeatures[heuristic_name]
         
      return self._availablefeatures
      

  def _tearDown(self, _, additionalParameters):
    basesubdir = additionalParameters["basesubdir"]
    candidates = additionalParameters["candidates"]
    
    
    #Write best result on the disk
    best = candidates[0]
    timingfile = open(CONF_TIMING_FILE_NAME, "w")
    timingfile.write(str(best.executionTime))
    timingfile.close()

    #Delete all the temporary files
    if CONF_DELETE_TEMP_DIR:
      for i in range(self.min_trial_number+1):
          dirname = os.path.join(basesubdir, str(i)+".tmp")
          shutil.rmtree(dirname, ignore_errors=True)


if __name__ == "__main__":
    
    (options, args) = parseCmdline()
    
    mylogger.configureLogging(options.logfile)
    
    if len(args)==0:
        print "Usage: learninggcc.py [options] benchmark"
        sys.exit(1)
                
    l = LearningGCC(use_mapreduce=options.usemapreduce,
                    knowledge=options.knowledge,
                    tmpdir=options.tmpdir,
                    min_trial_number=options.mintrialnumber,
                    generations=options.generations)

    program = os.path.abspath(args[0])
    res = l.compileProgram(program)
    l.close()
    exit(res)
