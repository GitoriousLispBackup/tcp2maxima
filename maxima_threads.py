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
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s %(process)d/%(threadName)s: %(message)s")
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class MaximaWorker(threading.Thread):
    """ A thread that controls a maxima instance and sends queries to it. """

    def __init__(self, name, sv):
        """Initializer. The supervisor sv owns the queue we use for queries.
        that's why we need it, too """
        threading.Thread.__init__(self);
        self.name = name
        self.sv = sv
        self.maxima = '/usr/bin/maxima'
        self.options = ['--very-quiet']
        self.process = sp.Popen([self.maxima] + self.options, stdin=sp.PIPE, stdout=sp.PIPE)
        self.stop = threading.Event()
         
    def run(self):
        while not self.stop.isSet():
            problem = self.sv.queries.get()
            prob_string = problem[0]
            callback = problem[1]
            
            # Add a semicolon at the line end if the user
            # didn't provide one
            # TODO: We need a lot more sanity checks 
            # on the input here!
            if prob_string[len(prob_string)-1] != ';':
                prob_string = prob_string + ';'
            
            # We record the time, when we start working
            self.sv.add_time(self.name, time.time())
            
            # Start processing stuff with maxima
            self.process.stdin.write(bytes(prob_string, "UTF-8"))                
            solution = self.process.stdout.readline()

            # We solved the problem, so remove the time
            self.sv.del_time(self.name)

            # Send the solution from maxima to the callback function
            solution = str(solution, "UTF-8").strip()
            if solution:
                callback(solution)
            else:
                callback("timeout")
        log.debug("Worker " + str(self.name) + " exits")

    def kill_worker(self):
        # TODO: How do we kill the worker but still send
        # a feedback to the callback function??
        # TODO: This leaves some weird sbcl zombie alive,
        # how do we kill that m****f****er????
        log.debug("Worker " + str(self.name) + " will be killed")
        self.process.terminate()
        # self.process.kill()
        self.stop.set()


    def _reset_maxima(self):
        self.process.stdin.write("reset();")
        self.process.stdin.write("kill(all);")


class MaximaSupervisor(threading.Thread):
    # Seconds after which to kill a worker
    # TODO: This should go in a proper config
    # file or something.
    timeout = 10 
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.workers = [MaximaWorker(i, self) for i in range(5)]
        self.queries = queue.Queue()        # The queue emptied by the maxima worker threads
        self.times = {}                     # Calculation times of the threads
        self.times_lock = threading.Lock()  # Here we need a lock for this
        self.stop = threading.Event()
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

            time.sleep(MaximaSupervisor.timeout)
            # Check threads sanity
            for worker in self.workers:
                self.times_lock.acquire()
                if worker.name in self.times.keys() \
                        and time.time() - self.times[worker.name] > MaximaSupervisor.timeout:
                    worker.kill_worker()
                    # TODO: Start new worker
                self.times_lock.release()
                
    def request(self, query, callback):
        self.queries.put([query, callback]) 

    def quit(self):
        self.stop.set()

# Keep this module executable for testing reasons
# If you try to run the server, this is not the 
# file to run!
def main():
    supervisor = MaximaSupervisor()
    supervisor.start()
    while True:
        query = input()
        supervisor.request(query, print)

    supervisor.quit()
    supervisor.join()



if __name__=='__main__':
    main()
