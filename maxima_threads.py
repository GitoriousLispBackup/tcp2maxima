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

# Python library imports
import fcntl
import logging
import os
import queue
import subprocess as sp
import threading
import time

# Local imports
import replyparser as rp
from requestfilter import RequestFilter

# Get a logger
# TODO: Still have to figure out how to connect this to the main
# logger when I use this as a module
logger = logging.getLogger("tcp2maxima")

ERROR_TIMEOUT = ";ERR;TIMEOUT"
ERROR_OUTPUT =  ";ERR;NO_OUTPUT"

class MaximaWorker(threading.Thread):
    """ A thread that controls a maxima instance and sends queries to it. """

    def __init__(self, name, queries, cfg):
        """Initializer. The supervisor sv owns the queue we use for queries.
        that's why we need it, too.
        """
        logger.debug("Starting Maxima " + str(name) + ".")
        threading.Thread.__init__(self);

        # Initialize instance
        self.cfg = cfg
        self.queries = queries
        self.parser = rp.ReplyParser(name) # I'm not sure but I think it's not thread safe to have only one global parser...
        self.name = name # Name of the thread, usually a integer
        self.options = [] 
        self.stop = threading.Event() # A event we use to stop our maxima worker
        self.fltr = RequestFilter()

        # Set up the list we use to start a maxima process. This depends on whether we
        # have to change the nice value of the maxima processes
        try:
            command = ['nice', '-n %s' % self.cfg['nice'], self.cfg['path']] + self.options 
        except KeyError:
            command = [self.cfg['path']] + self.options 

        # Start maxima and set up the process
        self.process = sp.Popen(command, stdin=sp.PIPE, stdout=sp.PIPE, bufsize=0, close_fds=True)
        # Setting the stdout pipe to non-blocking mode
        # TBH I have no idea how this works, but it does what I want.
        fcntl.fcntl(self.process.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

        # Read until ready
        try:
            self._get_maxima_reply()
        except TimeoutException:
            logger.error("Maxima %s didn't start correctly!" % self.name)

        # Initializing maxima
        self._init_maxima()

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
                    query = self.queries.get(block=False) # Pop a element from the queue.
                except queue.Empty:
                    pass
                time.sleep(.1)
                if self.stop.isSet():
                    break
            
            if self.stop.isSet():
                break

            response = query # The RequestController to send back the response
            request = response.request # The sting we want to send to maxima

            
            # Filter request with our request filter
            # TODO: What to do if the string isn't accepted?
            request = self.fltr.filter(request)
            
            # Start processing stuff with maxima
            logger.debug("Maxima " + self.name + " query: " + request)
            self._send_to_maxima(request)

            # Wait for a reply from maxima
            try:
                reply = self._get_maxima_reply()
                if reply:
                    response.set_reply(reply)
                else:
                    response.set_reply(ERROR_OUTPUT)
            except TimeoutException:
                response.set_reply(ERROR_TIMEOUT)
                self._restart_maxima()

            response.set_ready()
            # Tell the queue we're done. 
            self.queries.task_done()
                

        # Quit Maxima
        # self.process.terminate()
        # time.sleep(1)
        self.process.terminate()
        self.process.wait()
        # we need to actively delete the process object to really kill the process
        del self.process 
        logger.info("Worker " + str(self.name) + " exits")

    def quit_worker(self):
        """ Sets the event to stop the thread """
        logger.debug("Worker " + str(self.name) + " is about to exit.")
        self.stop.set()

    def _restart_maxima(self):
        # Kill the Maxima and start a new one
        logger.info("Maxima " + self.name + " timed out and will be killed.")
        # TODO: This should go somewhere else.
        self.process.kill()
        self.process.wait() # Wait for the return code
        del self.process
        self.process = sp.Popen([self.cfg['path']] + self.options, stdin=sp.PIPE, stdout=sp.PIPE, bufsize=0, close_fds=True)
        fcntl.fcntl(self.process.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
        logger.info("Maxima " + self.name + " started with a new Maxima process.")
        
        self._init_maxima()

    
    def _send_to_maxima(self, line):
        """Send a line to maxima, making sure there is a line end char at the end"""

        # Remove whitespaces at the end and append a line end character
        line = line.rstrip()
        line += "\n"
        
        # Send to stdin of Maxima and flush the cache
        self.process.stdin.write(bytes(line, "UTF-8"))
        self.process.stdin.flush()

    def _get_maxima_reply(self):
        """Read the output of Maxima"""

        # Used for timeout handling
        timeout = int(self.cfg['timeout'])
        start_stamp = time.time()        
        def _check_timeout():
            if time.time() - start_stamp > timeout:
                # Make sure the buffer is empty before we do anything
                # like killing a thread
                self.process.stdout.read()
                self.process.stdout.flush()
                raise TimeoutException
        # This method blocks if maxima doesn't return to a input
        # prompt. This is intended that we get a timeout if Maxima
        # doesn't like our query
        # Oh, and by the way: This code is ugly as hell!
        reply = None
        output = None
        ready = False

        logger.debug("Worker " + str(self.name) + " waits for Maxima reply.")
        while not output:
            _check_timeout()
            time.sleep(.1)
            self.process.stdout.flush()
            output = self.process.stdout.read()
        if output:
            logger.debug("Worker " + str(self.name) + " received: " +  str(output, "UTF-8", "replace"))
            reply, ready = self.parser.parse(str(output, "UTF-8", "replace"))

        # Basically just repeat what we did above.
        while not ready:
            logger.debug("Worker " + str(self.name) + " received a partial reply.")
            output = None
            logger.debug("Worker " + str(self.name) + " waiting for more data from Maxima.")
            while not output:
                _check_timeout()
                self.process.stdout.flush()
                output = self.process.stdout.read()
                time.sleep(.1)
            if output:
                logger.debug("Worker " + str(self.name) + " received: " + str(output, "UTF-8", "replace"))
                reply_tmp, ready = self.parser.parse(str(output, "UTF-8", "replace"))
                if reply_tmp and reply:
                    reply += "\n" + reply_tmp
                elif reply_tmp:
                    reply = reply_tmp
        logger.debug("Maxima " + str(self.name) + " sent full reply.")
        # Just in case something is stuck in the buffer, we make sure it's empty
        self.process.stdout.read()
        self.process.stdout.flush()
        return reply

    def _init_maxima(self):
        # Sends the init string to maxima
        logger.debug("Maxima " + str(self.name) + " init: " + self.cfg['init'])
        self._send_to_maxima(self.cfg['init'])
        
        # Read until ready
        try:
            self._get_maxima_reply()
        except TimeoutException:
            logger.error("Maxima %s didn't initialize correctly!" % self.name)


    def _reset_maxima(self):
        # Reset and re-init the maxima process
        # TODO: Check what we really need here.
        self._send_to_maxima(self.cfg['reset'])

        # Read until ready
        try:
            self._get_maxima_reply()
        except TimeoutException:
            logger.warn("Maxima %s failed to reset! Starting new instance." % self.name)
            self._restart_maxima()


class RequestController():
    """ RequestController are used to exchange data
    between the TCP server and the maxima worker threads
    """
    def __init__(self, request):
        # Event that is set by the worker as soon as
        # the Maxima output is ready
        self.ready = threading.Event()
        # Here we store the maxima output.
        self.reply = ''
        # Store the actual request.
        self.request = request
        
    def set_ready(self):
        self.ready.set()

    def is_ready(self):
        return self.ready.isSet()

    def wait(self):
        self.ready.wait()

    def set_reply(self, reply):
        self.reply = reply

    def get_reply(self):
        return self.reply

            

class TimeoutException(Exception):
    pass

class NoOutputException(Exception):
    pass



