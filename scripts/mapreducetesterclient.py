#!/usr/bin/env python
import os
import signal
import socket
import subprocess
import sys

PORT = 4242


def main(argv):
    server_ip = argv[1]
    client = Client(server_ip, PORT)

    client.register()
    
    while client.stay_alive:
        client.handle_message()
        
    client.close()
    
    
class Client(object):
    def __init__(self, ip, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, port))
        self.file = self.sock.makefile()
        self.server_ip = ip
        self.stay_alive = True
        self.previous_worker = None
        print "Client created"
        
    def register(self):
        self.send_string("ready")
        print "Client registered"
        
        
    def send_string(self, string):
        self.file.write(string)
        self.file.write("\n")
        self.file.flush()
        
        
    def handle_message(self):
        message = self.file.readline().strip()
        print "Received message: %s" % message
        
        if message == "run_worker":
            self._msg_run_worker()
        elif message == "quit":
            self.stay_alive = False
        
        
    def close(self):
        self.sock.close()
        
        
    def _msg_run_worker(self):
        self._kill_previous_worker()
        
        cmd = ["python",
               "mincemeat.py",
               self.server_ip]
               
        print "Executing: %s" % (" ".join(cmd))
        self.previous_worker = subprocess.Popen(cmd)
        
        
    def _kill_previous_worker(self):
        if not self.previous_worker:
            return
            
        if self.previous_worker.poll() is not None:
            #Process already terminated
            return
            
        kill_subprocess(self.previous_worker)
        print "Previous worker killed"
      
      
def kill_subprocess(p):
  if p.poll() is None:
    try:
      p.kill() #requires python 2.6
    except:
      os.kill(p.pid, signal.SIGKILL)
      
      
if __name__ == "__main__":
    main(sys.argv)