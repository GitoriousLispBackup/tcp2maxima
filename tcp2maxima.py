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

import configparser
import os
import signal
import sys
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


# These depend on the logger we just configured
from maxima_threads import MaximaSupervisor, RequestController
from tcp_server import ThreadedTCPServer, RequestHandler


class App:
    def __init__(self, config):
        logger.info("Initializing application.")
        # Initialize Maxima supervisor
        mxcfg = config['Maxima']
        # TODO: Send the whole maxima config over
        self.supervisor = MaximaSupervisor(mxcfg)

        # Initialize tcp server
        srvcfg = config['Server']
        # TODO: Send the whole server conf over
        self.host, self.port = srvcfg['address'], int(srvcfg['port'])
        self.server = ThreadedTCPServer((self.host, self.port), RequestHandler)
        # This is a ugly hack...
        # Of course this should go in the initializer
        # of this class. But sry, don't feel like it ATM.
        self.server.maxima = self.supervisor

    # This handler should handle SIGINT and SIGTERM
    # to gracefully exit the threads.
    def signal_handler(self, signal, frame):
        logging.warn("Received SIGTERM or SIGINT, trying to exit.")
        print('Trying to exit gracefully...')
        self.supervisor.quit()
        self.supervisor.join()
        sys.exit(0)

    # Start the Server
    def run(self):
        logger.debug("Starting Maxima supervisor")
        self.supervisor.start()
        logger.info("Starting TCP server on " + self.host + " listening to port " + str(self.port))
        self.server.serve_forever()

if __name__ == "__main__":
    app = App(config)
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    app.run()
