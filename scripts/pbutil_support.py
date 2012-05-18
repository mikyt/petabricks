import os
import subprocess
import threading
import time
import signal

def killSubprocess(p):
  if p.poll() is None:
    try:
      p.kill() #requires python 2.6
    except:
      os.kill(p.pid, signal.SIGKILL)
      
def terminateSubprocess(p):
  if p.poll() is None:
    try:
      p.terminate() #requires python 2.6
    except:
      os.kill(p.pid, signal.SIGTERM)

      
def timeoutKiller(subproc, timeout):
  """Kill the 'subproc' process after 'timeout' seconds"""
  
  endTime = time.time()+timeout
  
  while (subproc.poll() is None) and (time.time() < endTime):
      time.sleep(5)
  
  terminateSubprocess(subproc)
    
    
    
def compileBenchmark(pbc, src, binary=None, info=None, jobs=None, 
                     heuristics=None, timeout=None, defaultHeuristics=False,
                     knowledge=None, feature_directory=None):
    if not os.path.isfile(src):
      raise IOError("%s is not a file" % src)
    
    #Build the command
    cmd=[pbc]
    
    if binary is not None:
      cmd.append("--output="+binary)
    if info is not None:
      cmd.append("--outputinfo="+info)
    if jobs is not None:
      cmd.append("--jobs="+str(jobs))
    if heuristics is not None:
      cmd.append("--heuristics="+heuristics)
    if defaultHeuristics:
      cmd.append("--defaultheuristics")
    if knowledge:
        cmd.append("--knowledge=%s" % knowledge)
    if feature_directory:
        cmd.append("--featuredir=%s" % feature_directory)
        
    cmd.append(src)
    
    #Remove the output file (if it exists)
    if os.path.isfile(binary):
      os.unlink(binary)
      
    #Execute the compiler
    NULL=open("/dev/null", "w")
    
    print "Executing: %s" % " ".join(cmd)
    p = subprocess.Popen(cmd, stdout=NULL, stderr=NULL)
    
    if timeout is not None:
      #Start the timeout
      killerThread = threading.Thread(target=timeoutKiller, args=(p, timeout))
      killerThread.start()
    
    #Wait for the compiler to finish executing
    status = p.wait()
    
    return status
