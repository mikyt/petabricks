#!/usr/bin/python
"""Framework implementing long term learning of heuristics for the PetaBricks
compiler

Michele Tartara <mikyt@users.sourceforge.net>"""

import learningframework
import pbutil_support
import tunerwarnings
import logging
import mylogger
import optparse
import os
import pbutil
import sgatuner
import shutil
import subprocess

#------------------ Config --------------------
CONF_MAX_TIME = 60  # Seconds
CONF_DELETE_TEMP_DIR = True
CONF_TIMEOUT = 60
CONF_HEURISTIC_FILE_NAME = "heuristics.txt"
STATIC_INPUT_PREFIX = "learning_compiler_static"
NUM_TIMING_TESTS = 5
#----------------------------------------------


logger = logging.getLogger(__name__)

class Error(Exception):
    """Base exception class for this module, inherited by all the other 
    exceptions"""
    pass

class TimingRunError(Error):
    pass

def parseCmdline():
    parser = optparse.OptionParser(
        usage="usage: learningcompiler.py [options] testprogram"
    )
    parser.add_option("--heuristics",
                      type="string",
                      help="name of the file containing the set of heuristics to use",
                      default=None)
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
                            
    return parser.parse_args()

def create_static_input(program, input_size, static_input_name):
    assert input_size > 0
    
    cmd=[program, 
         "--n=%s" % input_size,
         "--iogen-create=%s" % static_input_name]
        
    print "Generating input files for the test program"
    NULL=open("/dev/null","w")
    logger.debug("Executing: %s" % cmd)
    p=subprocess.Popen(cmd, stdout=NULL, stderr=NULL)
    p.wait()
    NULL.close()
    
def test_with_static_input(program, trials, static_input_name, 
                           failure_retries=3):
    try:
        logger.info("Executing %s %d times, with static input", program, trials)
        res=pbutil.executeTimingRun(program, 
                                    trials=trials, 
                                    iogen_run=static_input_name)
        
        return res["average"]
    except pbutil.TimingRunFailed, e:
        if failure_retries==0:
            raise TimingRunError(e)
        
        return test_with_static_input(program, trials, static_input_name,
                                      failure_retries-1)
        
        
        
def compute_speedup(candidate, reference):
    (c_matrix_width, c_exec_time) = candidate
    (r_matrix_width, r_exec_time) = reference
        
    r_num_cells = r_matrix_width**2
    c_num_cells = c_matrix_width**2
    
    r_time_single_cell = r_exec_time / r_num_cells
    c_time_single_cell = c_exec_time / c_num_cells
    
    speedup = r_time_single_cell / c_time_single_cell
    return speedup
        
    
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
    basename = additionalParameters["basename"]
    pbc_exe = additionalParameters["pbc_exe"]
    threads = additionalParameters["threads"]
    static_input_name = additionalParameters["static_input_name"]
    dirnumber = count + 1    

    #The tuning has to reach the same size as the reference performance, but 
    #it could be slower. And the reference performance could have already 
    #reached the time limit. Therefore, allow for the double of the time limit
    #to be safe.
    max_tuning_size = additionalParameters["max_tuning_size"]
    max_tuning_time = 2*additionalParameters["max_tuning_time"]
    
    logger.info("Testing candidate %d", dirnumber)
    
    #Define more file names
    outDir = os.path.join(basesubdir, str(dirnumber))
    if not os.path.isdir(outDir):
        #Create the output directory
        os.makedirs(outDir)
    binary= os.path.join(outDir, basename)

    heuristicsFile= os.path.join(outDir, CONF_HEURISTIC_FILE_NAME)
    hSet.toXmlFile(heuristicsFile)

    status = pbutil_support.compileBenchmark(pbc_exe,
                                             benchmark,
                                             binary = binary,
                                             heuristics = heuristicsFile,
                                             jobs = threads,
                                             timeout = CONF_TIMEOUT)
    if status != 0:
        #Compilation has failed!
        #Take the data about the heuristics from the input heuristics file
        #instead of the info file (because there no such file!).
        #We are not sure that all the heuristics in the input
        #file have been used, but they had the compilation fail.
        #Their score is not increased, but they are marked as used
        #(and therefore they are penalized)
        logger.warning("Compile FAILED (%d) while using heuristic set #%d:", 
                       status, dirnumber)
        logger.warning(hSet.toXmlStrings())
        return learningframework.FailedCandidate(hSet, assignScores = False)


    #Autotune
    try:
        sgatuner.autotune_withparams(binary,
                                     n=max_tuning_size,
                                     max_time=max_tuning_time,
                                     threads=threads,
                                     delete_output_dir=True)
                                     
        #Fetch the actually used hSet
        infoFile = os.path.join(basesubdir,
                                str(dirnumber),
                                basename+".info")
        hSet = learningframework.HeuristicSet()
        hSet.importFromXml(infoFile)

        reference = additionalParameters["reference_performance"]    
        max_size = reference[0]
        execution_time = test_with_static_input(binary, 
                                                NUM_TIMING_TESTS, 
                                                static_input_name)    
        current_data = (max_size, execution_time)
        
        
        candidate = learningframework.SuccessfulCandidate(hSet)
        candidate.max_size = max_size
        candidate.executionTime = execution_time
        candidate.speedup = compute_speedup(current_data, reference)

        return candidate

    except tunerwarnings.AlwaysCrashes:
        logger.warning("Candidate %d always crashes during tuning with hset:", 
                       dirnumber)
        logger.warning(str(hSet))
        return learningframework.FailedCandidate(hSet, assignScores = True)
    except TimingRunError, e:
        logger.warning("Candidate %d failed during testing with static input:")
        logger.exception(e)
        return learningframework.FailedCandidate(hSet, assignScores = True)
    
    
    
    
class LearningCompiler(learningframework.Learner):
  _testHSet = staticmethod(test_heuristic_set)
  
  def __init__(self, pbcExe, heuristicSetFileName = None, threads = None, n=None, 
               maxTuningTime=None, use_mapreduce=True,
               min_trial_number=None):
    super(LearningCompiler, self).__init__(heuristicSetFileName, 
                                           use_mapreduce=use_mapreduce,
                                           min_trial_number=min_trial_number)
    
    self._pbcExe = pbcExe
    self._threads = threads
    self._n = n
    self.maxtuningtime = maxTuningTime

  @staticmethod
  def _candidateSortingKey(candidate):
      """Generates a comparison key for a candidate.
    Candidates are sorted by speedup wrt the reference candidate (compiled
    with default heuristics).
    The first candidate is the one with the bigger speedup"""
      if candidate.failed:
        return float('inf')
      return (1.0 / candidate.speedup)
  
  def _getMaxTuningSize(self):
      return self._n

  def _setMaxTuningSize(self, maxTuningSize):
      self._n = maxTuningSize
  
  def _getMaxTuningTime(self):
      return self._maxTuningTime
      
  def _setMaxTuningTime(self, maxTuningTime):
      if maxTuningTime:
          self._maxTuningTime = maxTuningTime
      else:
          self._maxTuningTime = CONF_MAX_TIME
  
  
  maxtuningsize = property(_getMaxTuningSize, _setMaxTuningSize)
  maxtuningtime = property(_getMaxTuningTime, _setMaxTuningTime)
  
  def compileProgram(self, benchmark, finalBinary = None, learn=True):
    self._finalBinary = finalBinary
    self._neededHeuristics=[]
    self._availablefeatures = None

    return self.use_learning(benchmark, learn)
    

  def _setup(self, benchmark, additionalParameters):
    #Define file names
    path, basenameExt = os.path.split(benchmark)
    if path == "":
      path="./"
    basename, ext = os.path.splitext(basenameExt)
    basesubdir = os.path.join(path,basename+".tmp")
    static_input_name = os.path.join(basesubdir, STATIC_INPUT_PREFIX)
    
    additionalParameters["basesubdir"] = basesubdir
    additionalParameters["basename"] = basename
    additionalParameters["static_input_name"] = static_input_name
    additionalParameters["path"] = path
    additionalParameters["pbc_exe"] = self._pbcExe
    additionalParameters["threads"] = self._threads
    additionalParameters["max_tuning_time"] = self.maxtuningtime
    candidates = additionalParameters["candidates"]
    
    #Compile with default heuristics
    outDir = os.path.join(basesubdir, "0")
    if not os.path.isdir(outDir):
      #Create the output directory
      os.makedirs(outDir)
    binary= os.path.join(outDir, basename)
    status = pbutil_support.compileBenchmark(self._pbcExe,
                                             benchmark,
                                             binary = binary,
                                             jobs = self._threads,
                                             defaultHeuristics = True)
    if status != 0:
      logger.error("Compile FAILED with default heuristics (status: %d)- "
                   "Compilation aborted", (status))
      return status

    #Autotune
    try:
        tuned_candidate = sgatuner.autotune_withparams(binary, 
                                                   n=self._n, 
                                                   max_time=self._maxTuningTime,
                                                   delete_output_dir=True)

        #Fetch the actually used set of heuristics
        infoFile = os.path.join(outDir, basename+".info")
        h_set = learningframework.HeuristicSet()
        h_set.importFromXml(infoFile)
        
        max_tuned_size = tuned_candidate.maxMatrixSize()
        additionalParameters["max_tuning_size"] = max_tuned_size
        
        max_test_size = self._n if self._n else max_tuned_size
        create_static_input(binary, max_test_size, static_input_name)
        
        
        execution_time = test_with_static_input(binary, 
                                                NUM_TIMING_TESTS,
                                                static_input_name)
                
        default_candidate = learningframework.SuccessfulCandidate(h_set)
        default_candidate.speedup = 1 #This is the reference for the speedup
        default_candidate.originalIndex = -1
        default_candidate.max_size = max_test_size
        default_candidate.executionTime = execution_time
       
        candidates.append(default_candidate)
        
        #Store for later use by the candidates        
        additionalParameters["reference_performance"] = (max_test_size, 
                                                         execution_time)
        
        logger.info("The reference performance with default heuristics is %s",
                    (additionalParameters["reference_performance"]))        
        
        #Get the full set of available features
        self._availablefeatures = learningframework.AvailableFeatures()
        self._availablefeatures.importFromXml(infoFile)
    
        #Store the list of needed heuristics for the current benchmark
        self._neededHeuristics = []
        for name, heur in h_set.iteritems():
            available_features = self._get_available_features(benchmark, name)
            neededheur = heur.derive_needed_heuristic(available_features)
            self._neededHeuristics.append(neededheur)        
            
        return 0        
        
    except tunerwarnings.AlwaysCrashes:
        logger.error("Autotuning with default heuristics always crashes!")
        return -1
    except TimingRunError, e:
        logger.warning("Default candidate failed during testing with static "
                       "input:")
        logger.exception(e)
        return -1
    


  def _getNeededHeuristics(self, unused_benchmark):
    return self._neededHeuristics


  def _get_available_features(self, unused_benchmark, heuristic_name=None):
      if heuristic_name is not None:
          return self._availablefeatures[heuristic_name]
         
      return self._availablefeatures
      

  def _tearDown(self, _, additionalParameters):
    candidates = additionalParameters["candidates"]
    basesubdir = additionalParameters["basesubdir"]
    basename = additionalParameters["basename"]
    path = additionalParameters["path"]

    if len(candidates) != 0:
        bestIndex = candidates[0].originalIndex + 1
    else:
        #No need for heuristics: just use the default executable
        bestIndex = 0
    logger.info("The best candidate is: %d", bestIndex)

    #Move every file to the right place
    bestSubDir = os.path.join(basesubdir, str(bestIndex))
    #  compiled program:
    bestBin = os.path.join(bestSubDir, basename)
    if self._finalBinary is not None:
      finalBin = self._finalBinary
    else:
      finalBin = os.path.join(path, basename)
    logger.debug("Final binary: %s -> %s", bestBin, finalBin)
    shutil.move(bestBin, finalBin)
    #  .info file
    bestInfo = os.path.join(bestSubDir, basename+".info")
    finalInfo = finalBin+".info"
    logger.debug("Moving .info")
    shutil.move(bestInfo, finalInfo)
    #  .obj directory
    bestObjDir = os.path.join(bestSubDir, basename+".obj")
    destObjDir = finalBin+".obj"
    if os.path.isdir(destObjDir):
      logger.debug("Remove old objdir")
      shutil.rmtree(destObjDir)
    logger.debug("Move objdir")
    shutil.move(bestObjDir, destObjDir)
    if bestIndex != 0:
        #Deal with the following files only if the executable was compiled 
        #with some heuristics
        
        #  .cfg file
        bestCfg = os.path.join(bestSubDir, basename+".cfg")
        finalCfg = finalBin + ".cfg"
        logger.debug("Move final cfg")
        shutil.move(bestCfg, finalCfg)
        #  input heuristic file
        bestHeurFile = os.path.join(bestSubDir, CONF_HEURISTIC_FILE_NAME)
        finalHeurFile = finalBin+".heur"
        logger.debug("Move final heuristic file")
        shutil.move(bestHeurFile, finalHeurFile)

    #Delete all the rest
    if CONF_DELETE_TEMP_DIR:
      logger.debug("Delete the temp dir")
      shutil.rmtree(basesubdir, ignore_errors=True)



#TEST
if __name__ == "__main__":
    import sys
    
    script_path = sys.path[0]
    petabricks_path = os.path.join(script_path, "../")
    petabricks_path = os.path.normpath(petabricks_path)
    examples_path= os.path.join(petabricks_path, "examples")  
    pbc = os.path.join(petabricks_path,"src/pbc")
    
    (options, args) = parseCmdline()
    
    mylogger.configureLogging(options.errorfile)
    
    if len(args)==0:
        print "Usage: learningcompiler.py [options] testprogram.pbcc"
        sys.exit(1)
                
    l = LearningCompiler(pbc,
                         heuristicSetFileName = options.heuristics,
                         n=options.maxtuningsize,
                         maxTuningTime=options.maxtuningtime,
                         threads = options.threads,
                         use_mapreduce = options.usemapreduce,
                         min_trial_number = options.mintrialnumber)

    program = os.path.abspath(args[0])
    l.compileProgram(program)
    l.close()