# This file is part of tcp2maxima.
#
#    Copyright (c) 2013 Beni Keller
#    Distributed under the GNU GPL v3. For full terms see the file gpl.txt.
#
#    tcp2maxima is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    tcp2maxima is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with tcp2maxima.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import subprocess as sp
import threading
import queue
import time

# Get a logger
# TODO: Still have to figure out how to connect this to the main
# logger when I use this as a module
logger = logging.getLogger("tcp2maxima")

class MaximaWorker(threading.Thread):
    """ A thread that controls a maxima instance and sends queries to it. """

    def __init__(self, name, sv):
        """Initializer. The supervisor sv owns the queue we use for queries.
        that's why we need it, too.
        """
        logger.debug("Starting Maxima worker thread " + str(name) + ".")
        threading.Thread.__init__(self);
        self.name = name # Name of the thread, usually a integer
        self.sv = sv # The supervisor of the threads
        self.options = ['--very-quiet'] # We don't want Maxima to report the version at startup
        self.process = sp.Popen([sv.cfg['path']] + self.options, stdin=sp.PIPE, stdout=sp.PIPE)
        self.stop = threading.Event() # A event we use to stop our maxima worker
        
        # Initialize maxima with the init string form the configuration
        self.process.stdin.write(bytes(sv.cfg['init'], "UTF-8"))
         
    def run(self):
        """ Starts the loop which pops elements off the queue. 
        Runs until the stop event is sent from kill_worker().
        """
        logger.debug("Maxima worker " + str(self.name) + " starts processing queries")
        while not self.stop.isSet():
            query = self.sv.queries.get() # Pop a element from the queue.
            request = query[0] # The sting we want to send to maxima
            response = query[1] # The RequestController to send back the response
            
            # Add a semicolon at the line end if the user
            # didn't provide one
            # TODO: We need a lot more sanity checks 
            # on the input here! !!!!!
            if request == '' or request[len(request)-1] != ';':
                request = request + ';'
            
            # We record the time, when we start working
            self.sv.add_time(self.name, time.time())
            
            # Start processing stuff with maxima
            self.process.stdin.write(bytes(request, "UTF-8"))                
            solution = self.process.stdout.readline()

            # We solved the problem, so remove the time
            self.sv.del_time(self.name)

            solution = str(solution, "UTF-8").strip()
            if solution:
                response.set_reply(solution)
            else:
                response.set_reply("timeout")
            # Set the event to signal the server that we are ready.
            response.set_ready()
            # TODO: We should tell the queue that we are done processing the element.

        # TODO: This leaves some weird sbcl zombie alive,
        # how do we kill that m****f****er????
        self.process.terminate()
        # we need to actively delete the process object to really kill the process
        del self.process 
        logger.info("Worker " + str(self.name) + " exits")

    def kill_worker(self):
        """ Sets the event to stop the thread """
        logger.debug("Worker " + str(self.name) + " will be (ex)terminated")
        self.process.terminate()
        self.stop.set()

    def _reset_maxima(self):
        # Reset and re-init the maxima process
        # TODO: Check what we really need here.
        self.process.stdin.write("reset();")
        self.process.stdin.write("kill(all);")
        self.process.stdin.write(sv.cfg['init'])


class MaximaSupervisor(threading.Thread):
    """ Class which controlls the Maxima worker threads. """
    
    def __init__(self, cfg):
        threading.Thread.__init__(self)

        # Configuration for the workers
        self.cfg = cfg # Multiline init string for Maxima
        
        # The queue that holds the maxima queries which are sent to 
        # Maxima by the worker threads.
        # A query is a 2-tuple consisting of:
        # 0. The actual string that's sent to maxima
        # 1. A RequestController object used to reply to the TCP server
        self.queries = queue.Queue()        
        self.times = {} # Calculation times of the threads
        self.times_lock = threading.Lock() # Here we need a lock for this
        self.stop = threading.Event()
        self.workers = [MaximaWorker(i, self) for i in range(int(cfg['threads']))]
        for worker in self.workers:
            worker.setDaemon(True) 
            worker.start() 
            
    # Add a starting time for a certain thread
    # used to track the time a thread works
    def add_time(self, thread, time):
        self.times_lock.acquire()
        self.times[thread] = time
        self.times_lock.release()

    # Call this when a thread gets something back
    # from Maxima. 
    def del_time(self, thread):
        self.times_lock.acquire()
        del self.times[thread]
        self.times_lock.release()
            
    def run(self):
        while not self.stop.isSet(): 

            time.sleep(int(self.cfg['timeout']))
            # Check threads sanity
            for worker in self.workers:
                self.times_lock.acquire()
                if worker.name in self.times.keys() \
                        and time.time() - self.times[worker.name] > int(self.cfg['timeout']):
                    logger.warn("Maxima worker " + str(worker.name) + " timed out.")
                    worker.kill_worker()
                    # TODO: Start new worker
                self.times_lock.release()
                
    def request(self, query, callback):
        self.queries.put([query, callback]) 

    def quit(self):
        self.stop.set()


class RequestController:
    """ RequestController are used to exchange data
    between the TCP server and the maxima worker threads

    Objects are not initialized here but by the TCP server
    but it's more logical to keep this class here...
    """
    def __init__(self):
        # Event that is set by the worker as soon as
        # the Maxima output is ready
        self.ready = threading.Event()
        # Here we store the maxima output.
        self.reply = ''

    def set_ready(self):
        self.ready.set()

    def is_ready(self):
        return self.ready.isSet()

    def set_reply(self, reply):
        self.reply = reply

    def get_reply(self):
        return self.reply

