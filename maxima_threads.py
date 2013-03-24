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
import fcntl
import os
import replyparser as rp

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
        logger.debug("Starting Maxima " + str(name) + ".")
        threading.Thread.__init__(self);

        # Initialize instance
        self.parser = rp.ReplyParser(name) # I'm not sure but I think it's not thread safe to have only one global parser...
        self.name = name # Name of the thread, usually a integer
        self.sv = sv # The supervisor of the threads
        self.options = [] # We don't want Maxima to report the version at startup
        self.stop = threading.Event() # A event we use to stop our maxima worker
        # Start maxima and set up the process
        self.process = sp.Popen([sv.cfg['path']] + self.options, stdin=sp.PIPE, stdout=sp.PIPE, bufsize=0)
        # Setting the stdout pipe to non-blocking mode
        # TBH I have no idea how this works, but it does what I want.
        fcntl.fcntl(self.process.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

        # Read until ready
        self._get_maxima_reply()

        # Initializing maxima
        logger.debug("Maxima " + str(name) + ": Writing init string to Maxima.")
        self.process.stdin.write(bytes(sv.cfg['init'], "UTF-8"))
        
        # Read until ready
        self._get_maxima_reply()

    def run(self):
        """ Starts the loop which pops elements off the queue. 
        Runs until the stop event is sent from kill_worker().
        """
        logger.info("Maxima" + str(self.name) + " starts processing queries")
        while not self.stop.isSet():
            # Reset maxima for the next query
            self._reset_maxima()

            # Don't block while reading the queue because we want to be able to exit
            query = None
            while not query:
                try:
                    query = self.sv.queries.get(block=False) # Pop a element from the queue.
                except queue.Empty:
                    pass
                time.sleep(.1)
                if self.stop.isSet():
                    continue
                    break

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
            logger.debug("Maxima " + self.name + " query: " + request)
            self.process.stdin.write(bytes(request, "UTF-8"))                

            # Wait for a reply from maxima
            reply = self._get_maxima_reply()

            # We solved the problem, so remove the time
            self.sv.del_time(self.name)
            
            if reply:
                response.set_reply(reply)
            else:
                response.set_reply("Timeout")
            # Set the event to signal the server that we are ready.
            response.set_ready()
            # Tell the queue we're done. 
            self.sv.queries.task_done()
                

        # Quit Maxima
        self.process.terminate()
        time.sleep(1)
        self.process.kill()
        # we need to actively delete the process object to really kill the process
        del self.process 
        logger.info("Worker " + str(self.name) + " exits")

    def quit_worker(self):
        """ Sets the event to stop the thread """
        logger.debug("Worker " + str(self.name) + " is about to exit.")
        self.stop.set()

    
    def _get_maxima_reply(self):
        """Read the output of Maxima"""
        # This method blocks if maxima doesn't return to a input
        # prompt. This is intended that we get a timeout if Maxima
        # doesn't like our query
        # Oh, and by the way: This code is ugly as hell!
        reply = None
        output = None
        ready = False
        logger.debug("Worker " + str(self.name) + " waits for Maxima reply.")
        while not output and not self.stop.isSet():
            output = self.process.stdout.read()
            self.process.stdout.flush()
            time.sleep(.1)
        if output:
            reply, ready = self.parser.parse(str(output, "UTF-8"))

        # Basically just repeat what we did above.
        while not ready and not self.stop.isSet():
            logger.debug("Worker " + str(self.name) + " received a partial reply.")
            output = None
            logger.debug("Worker " + str(self.name) + " waiting for more data from Maxima.")
            while not output and not self.stop.isSet():
                output = self.process.stdout.read()
                self.process.stdout.flush()
                time.sleep(.1)
            if output:
                reply_tmp, ready = self.parser.parse(str(output, "UTF-8"))
                if reply_tmp and reply:
                    reply += "\n" + reply_tmp
                elif reply_tmp:
                    reply = reply_tmp
        logger.debug("Worker " + str(self.name) + " received full reply from Maxima or is forced to quit.")
        return reply

    def _reset_maxima(self):
        # Reset and re-init the maxima process
        # TODO: Check what we really need here.
        self.process.stdin.write(b"reset();")
        self.process.stdin.write(b"kill(all);")
        self.process.stdin.write(bytes(self.sv.cfg['init'], "UTF-8"))

        # Read until ready
        self._get_maxima_reply()


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
        logger.info("Starting Maxima supervisor.")
        while not self.stop.isSet(): 
            time.sleep(2) 
            # Check threads sanity
            for i in range(len(self.workers)):
                worker = self.workers[i]
                self.times_lock.acquire()
                if worker.name in self.times.keys() \
                        and time.time() - self.times[worker.name] > int(self.cfg['timeout']):
                    logger.warn("Maxima worker " + str(worker.name) + " timed out.")
                    worker.quit_worker()
                    worker.join() # Only for debugging! Needs to go away afterwards!
                    del worker
                    self.workers[i] = MaximaWorker(i, self)
                    self.del_time(i)
                self.times_lock.release()
        # We want to quit the superviser. 
        # Wait for the queue to be emptied
        logger.info("Quitting Maxima supervisor.")
        logger.debug("Waiting for the querie queue to be emtpied.")
        self.queries.join()
        logger.debug("Quitting the Maxima workers.")
        for worker in self.workers:
            worker.quit_worker()
            # worker.join() <- Would be nice, but doesn't work because of the blocking get on the Queue
                
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

