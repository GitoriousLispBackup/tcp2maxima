#! env python

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

import argparse
import configparser
import os
import queue
import signal
import threading
import sys
import time
import logging

##########################
### Load configuration ###
##########################
config = configparser.ConfigParser()
# Read the default configuration 
# if this doesn't exist it's not good.
config.readfp(open('default.cfg'))

# read alternative configuration files
alt_path = ['/etc/tcp2maxima.cfg']
alt_path.append('/etc/tcp2maximarc')
alt_path.append(os.path.expanduser('~/.tcp2maxima.cfg'))
alt_path.append(os.path.expanduser('~/.tcp2maximarc'))
config.read(alt_path)

##########################
### Configure logger   ###
##########################
logging.basicConfig(level=config['Logging']['level'])
logger = logging.getLogger("tcp2maxima")
# TODO: Loggin to file... 
# handler = logging.FileHandler(config['Logging']['file'])

# Used to count SIGTERMS
signal_count = 0

# These depend on the logger we just configured
from maxima_threads import MaximaWorker
from tcp_server import ThreadedTCPServer, RequestHandler

########################################
### Configure command line arguments ###
########################################

# Configure the command line parser and the command line options
parser = argparse.ArgumentParser(description='A threading tcp interface to Maxima instances.')
parser.add_argument('-d', '--daemon', 
                    dest='daemon',
                    action='store_true',
                   help='run as a deamon process')
parser.add_argument('--user', dest='user', default=False,
                    help="set user who owns the process (might not work unless run as root)")

args = parser.parse_args()

# Global configuration extracted from command line options and in some
# parts from the configuration file.
cfg = {}
cfg['daemon'] = config.getboolean('General', 'daemon') or args.daemon
cfg['user'] = args.user


########################################
### Main application                 ###
########################################


class App:
    """The main application"""
    def __init__(self, config):
        logger.info("Initializing application.")
        self.stop = False # Use to stop application
        # Initialize Maxima supervisor
        self.mxcfg = config['Maxima']
        # Queue used to send request to the maxima instances
        self.queries = queue.Queue()      

        # Initialize tcp server
        srvcfg = config['Server']
        self.host, self.port = srvcfg['address'], int(srvcfg['port'])
        # Create a simple request factory on the spot
        mycallback = lambda query, controller: self.queries.put((query, controller))
        get_handler = lambda *args, **keys: RequestHandler(mycallback, *args, **keys)
        self.server = ThreadedTCPServer((self.host, self.port), get_handler)

    # This handler should handle SIGINT and SIGTERM
    # to gracefully exit the threads.
    def signal_handler(self, signal, frame):
        global signal_count
        
        # Hitting ctrl-c multiple times forces to quit.
        if signal_count > 0:
            logger.warn("User is in impatient, forcing exit.")
            sys.exit(1)
        signal_count +=1
        logger.warn("Received SIGTERM or SIGINT, trying to exit.")
        self.stop = True
        
    # Start the Server
    def run(self):
        logger.info("Starting " + self.mxcfg['threads'] + " Maxima threads.")
        self.workers = [MaximaWorker(i, self.queries, self.mxcfg) for i in range(int(self.mxcfg['threads']))]
        for worker in self.workers:
            worker.setDaemon(True) 
            worker.start() 

        logger.info("Starting TCP server on " + self.host + " listening to port " + str(self.port))
        # Cant shut down the server, that's why I create a thread for now.
        # self.server.serve_forever()
        

        server_thread = threading.Thread(target=self.server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()

        # Just wait for someone to quit the application.
        while self.stop == False:
            time.sleep(.5)

        # Quitting after tcp server shutdown
        self.queries.join()
        logger.debug("Quitting the Maxima workers.")
        for worker in self.workers:
            worker.quit_worker()
            worker.join() 
        

if __name__ == "__main__":
    app = App(config)
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    app.run()
