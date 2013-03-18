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

from maxima_threads import MaximaSupervisor, RequestController
from tcp_server import ThreadedTCPServer, RequestHandler

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

class App:

    def __init__(self, config):
        # Initialize Maxima supervisor
        mxcfg = config['Maxima']
        self.supervisor = MaximaSupervisor(mxcfg['executable'], mxcfg['init'])

        # Initialize tcp server
        srvcfg = config['Server']
        host, port = srvcfg['address'], srvcfg['port']
        self.server = ThreadedTCPServer((host, port), RequestHandler)
        # This is a ugly hack...
        # Of course this should go in the initializer
        # of this class. But sry, don't feel like it ATM.
        self.server.maxima = self.supervisor

    # This handler should handle SIGINT and SIGTERM
    # to gracefully exit the threads.
    def signal_handler(signal, frame):
        print('Trying to exit gracefully...')
        self.supervisor.quit()
        self.supervisor.join()
        sys.exit(0)

    # Start the Server
    def run(self):
        self.supervisor.start()
        self.server.serve_forever()

if __name__ == "__main__":
    app = App(config)
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    app.run()
