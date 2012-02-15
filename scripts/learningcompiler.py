#!/usr/bin/python
"""Framework implementing long term learning of heuristics for the PetaBricks
compiler

Michele Tartara <mikyt@users.sourceforge.net>"""

import learningframework
import os
import pbutil_support
import tunerwarnings
import shutil
import sgatuner
import logging
import mylogger

#------------------ Config --------------------
CONF_MAX_TIME = 60  # Seconds
CONF_DELETE_TEMP_DIR = True
CONF_TIMEOUT = 60
CONF_HEURISTIC_FILE_NAME = "heuristics.txt"
#----------------------------------------------


logger = logging.getLogger(__name__)


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
    dirnumber = count + 1    

    #The tuning has to reach the same size as the reference performance, but 
    #it could be slower. And the reference performance could have already 
    #reached the time limit. Therefore, allow for the double of the time limit
    #to be safe.
    max_tuning_size = additionalParameters["reference_performance"][0]
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
        tuned_candidate = sgatuner.autotune_withparams(binary,
                                                       n=max_tuning_size,
                                                       max_time=max_tuning_time,
                                                       threads=threads)
    except tunerwarnings.AlwaysCrashes:
        logger.warning("Candidate %d always crashes during tuning with hset:", 
                       dirnumber)
        logger.warning(str(hSet))
        return learningframework.FailedCandidate(hSet, assignScores = True)


    #Fetch the actually used hSet
    infoFile = os.path.join(basesubdir,
                            str(dirnumber),
                            basename+".info")
    hSet = learningframework.HeuristicSet()
    hSet.importFromXml(infoFile)
    
    #Return the candidate
    candidate = learningframework.SuccessfulCandidate(hSet)

    max_size = tuned_candidate.maxMatrixSize()
    executionTime = tuned_candidate.timingResults().mean()
    
    reference = additionalParameters["reference_performance"]
    
    candidate.speedup = compute_speedup((max_size, executionTime), 
                                        reference)
    candidate.max_size = max_size
    candidate.executionTime = executionTime

    return candidate
    
    
    
class LearningCompiler(learningframework.Learner):
  _testHSet = staticmethod(test_heuristic_set)
  
  def __init__(self, pbcExe, heuristicSetFileName = None, threads = None, n=None, 
               maxTuningTime=CONF_MAX_TIME, use_mapreduce=True):
    super(LearningCompiler, self).__init__(heuristicSetFileName, 
                                           use_mapreduce=use_mapreduce)
    
    self._pbcExe = pbcExe
    self._threads = threads
    self._n = n
    self._maxTuningTime = maxTuningTime

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
      self._maxTuningTime = maxTuningTime
  
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
    additionalParameters["basesubdir"] = basesubdir
    additionalParameters["basename"] = basename
    additionalParameters["path"] = path
    additionalParameters["pbc_exe"] = self._pbcExe
    additionalParameters["threads"] = self._threads
    additionalParameters["max_tuning_time"] = self._maxTuningTime
    
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
                                     max_time=self._maxTuningTime)

        #Fetch the actually used hSet
        infoFile = os.path.join(outDir, basename+".info")
        h_set = learningframework.HeuristicSet()
        h_set.importFromXml(infoFile)
        
        default_candidate = learningframework.SuccessfulCandidate(h_set)
        default_candidate.speedup = 1 #This is the reference for the speedup
        default_candidate.originalIndex = -1
        candidates.append(default_candidate)
        
        #Store for later use by the candidates
        max_size = tuned_candidate.maxMatrixSize()
        executionTime = tuned_candidate.timingResults().mean()
        
        additionalParameters["reference_performance"] = (max_size, 
                                                         executionTime)
        
        logger.info("The reference performance with default heuristics is %s",
                    (additionalParameters["reference_performance"]))
        
        default_candidate.max_size = max_size
        default_candidate.executionTime = executionTime

        
    except tunerwarnings.AlwaysCrashes:
      logger.error("Autotuning with default heuristics always crashes!")
      return -1

    #Get the full set of used heuristics and available features
    infoFile = binary+".info"
    currentDefaultHSet = learningframework.HeuristicSet()
    currentDefaultHSet.importFromXml(infoFile)
    self._availablefeatures = learningframework.AvailableFeatures()
    self._availablefeatures.importFromXml(infoFile)
    
    #Store the list of needed heuristics for the current benchmark
    self._neededHeuristics = []
    for name, heur in currentDefaultHSet.iteritems():
        available_features = self._get_available_features(benchmark, name)
        neededheur = heur.derive_needed_heuristic(available_features)
        self._neededHeuristics.append(neededheur)

    return 0


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
    shutil.move(bestBin, finalBin)
    #  .info file
    bestInfo = os.path.join(bestSubDir, basename+".info")
    finalInfo = finalBin+".info"
    shutil.move(bestInfo, finalInfo)
    #  .obj directory
    bestObjDir = os.path.join(bestSubDir, basename+".obj")
    destObjDir = finalBin+".obj"
    if os.path.isdir(destObjDir):
      shutil.rmtree(destObjDir)
    shutil.move(bestObjDir, destObjDir)
    if bestIndex != 0:
        #Deal with the following files only if the executable was compiled 
        #with some heuristics
        
        #  .cfg file
        bestCfg = os.path.join(bestSubDir, basename+".cfg")
        finalCfg = finalBin + ".cfg"
        shutil.move(bestCfg, finalCfg)
        #  input heuristic file
        bestHeurFile = os.path.join(bestSubDir, CONF_HEURISTIC_FILE_NAME)
        finalHeurFile = finalBin+".heur"
        shutil.move(bestHeurFile, finalHeurFile)

    #Delete all the rest
    if CONF_DELETE_TEMP_DIR:
      shutil.rmtree(basesubdir, ignore_errors=True)



#TEST
if __name__ == "__main__":
    import sys
    
    script_path = sys.path[0]
    petabricks_path = os.path.join(script_path, "../")
    petabricks_path = os.path.normpath(petabricks_path)
    examples_path= os.path.join(petabricks_path, "examples")  
    pbc = os.path.join(petabricks_path,"src/pbc")
    errorfile = pbc + "/error-log.dat"
    
    mylogger.configureLogging(errorfile)
    
    if len(sys.argv)==1:
        print "Usage: learningcompiler.py program.pbcc [heuristicSetFileName]"
        sys.exit(1)
        
    try:
        heuristics = sys.argv[2]
    except:
        heuristics = None
        
    l = LearningCompiler(pbc, 
                         heuristicSetFileName = heuristics, 
                         use_mapreduce=False)
    l.compileProgram(sys.argv[1])
