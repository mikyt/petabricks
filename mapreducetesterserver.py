#!/usr/bin/env python
"""Executes petabricks in mapreduce mode, keeping a connection between the 
master node and the client nodes. The connection is used to start multiple tests
automatically, each time executing a new mapreduce server and new clients"""


import logging
import optparse
import os
import sys
import threading
import time
import SocketServer
import subprocess

logger = logging.getLogger(__name__)
    
def main():
    """The body of the program"""

    petabricks_path = sys.path[0]
    scripts_path = os.path.join(petabricks_path, "scripts")

    (options, args) = parsecmdline()

    configure_logging(scripts_path, options.logfile)
    
    HOST, PORT = "localhost", 4242
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    
    logger.debug("Server loop running in thread: %s", server_thread.name)
    
    #Wait for client connections
    time.sleep(15)
    
    testrunner = TestRunner(server, options.resultfile)
    testrunner.run_tests(options.maxheurnumber)
    testrunner.close()
    
    server.shutdown()
    
    
def configure_logging(scripts_path, errorfile):
    sys.path.append(scripts_path)
    import mylogger
    mylogger.configureLogging(errorfile)
    
    
def parsecmdline():
    parser = optparse.OptionParser(usage="usage: mapreducetestserver.py [options] testprogram")
    parser.add_option("--logfile",
                      type="string",
                      help="file containing the log of errors",
                      default="mapreducetesterserver.log")
    parser.add_option("--resultfile",
                      type="string",
                      help="file containing the results in gnuplot-compatible format",
                      default="mapreduce-results.dat")
    parser.add_option("--maxheurnumber",
                      type="int", 
                      help=("maximum number of heuristics to be generated for "
                            "the tests"),
                      default=16)
    return parser.parse_args()
    
        
class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        self.stay_alive = True
        #Main function, handling the connection
        while self.stay_alive:
            message = self.rfile.readline().strip()
            logger.debug("Received(%d): %s", len(message), message)
            
            if message == "ready":
                self._msg_ready()
    
    def _msg_ready(self):
        logger.info("Client ready: %s", self.client_address)
        self.server.ready_connections.append(self)

    def run_worker(self):
        command = "run_worker"
        self.send_string(command)
        
    def send_string(self, string):
        self.wfile.write(string)
        self.wfile.write("\n")
        
    def quit(self):
        self.stay_alive = False
        
        
        

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    ready_connections = []
    
    def max_worker_nodes(self):
        return len(self.ready_connections)
        

        
class TestRunner(object):
    def __init__(self, server, outfilename):
        self.server = server
        self.outfile = file(outfilename, "w")
    
    
    def run_tests(self, max_heuristics):
        self._print_result_file_header()
        for i in range(4, max_heuristics+1):
            #The minimum number of heuristics used is 4
            #It's pointless to test with less than 4: the learner would use 4 
            #heuristics anyway!
            self._run_tests_with_n_heuristics(i)
    
    
    def close(self):
        self.outfile.close()
        
        
    def _print_result_file_header(self):
        self.outfile.write("Heuristics_number\t")
        max_worker_nodes = self.server.max_worker_nodes()
        for i in range(max_worker_nodes):
            self.outfile.write("Worker_%s\t" % str(i+1))
        self.outfile.write("\n")
        
        
    def _run_tests_with_n_heuristics(self, num_heuristics):
        
        self.outfile.write("%d\t" % num_heuristics)
        
        max_worker_nodes = self.server.max_worker_nodes()
        for i in range(1, max_worker_nodes+1):
            running_time = self._average_run_tests_on_limited_nodes(num_heuristics, 
                                                                    num_nodes=i,
                                                                    trials=3)
            self.outfile.write("%d\t" % running_time)
        
        self.outfile.write("\n")
        
    
    def _average_run_tests_on_limited_nodes(self, num_heuristics, num_nodes, 
                                           trials):
        total_time = 0
        for i in range(trials):
            print "Execution %d/%d" % (i, trials)
            running_time = self._run_tests_on_limited_nodes(num_heuristics, 
                                                            num_nodes)
            total_time += running_time
            
            #Avoid TIME_WAIT problems for TCP connections
            #time.sleep(60)
            
        average_time = total_time / trials
        return average_time
         
         
    def _run_tests_on_limited_nodes(self, num_heuristics, num_nodes):
        print "Running tests on %d heuristics using %d workers" % (
            num_heuristics, num_nodes)
        
        start_time = time.time()
        #TODO main_node = self._run_main_node(num_heuristics)
        
        for i in range(num_nodes):
            self._run_worker_node(i)
    
        #TODO main_node.wait()
        end_time = time.time()
        
        running_time = end_time - start_time
        return running_time
        
        
    def _run_main_node(self, num_heuristics):
        maxtuningsize=4
        mintrialnumber=4
        threads=8
        program = "examples/simple/rollingsum.pbcc"
        
        cmd = ["./scripts/learningcompiler.py",
               "--maxtuningsize=%d" % maxtuningsize,
               "--mintrialnumber=%d" % mintrialnumber,
               "--threads=%d" % threads,
               "--mintrialnumber=%d" % num_heuristics,
               "--usemapreduce",
               program]
               
        logger.debug("Running main node: %s", " ".join(cmd))
        #TODO main_node = subprocess.Popen(cmd)
        
        #TODO return main_node
    
    
    def _run_worker_node(self,i):
        connection = self.server.ready_connections[i]
        
        logger.info("Asking worker node on %s to start", connection.client_address)
        connection.run_worker()
        

if __name__ == "__main__":
    main()
