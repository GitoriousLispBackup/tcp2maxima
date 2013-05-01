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

# Remark: At the moment this module doesn't do any logging.
# That's because it wasn't needed yet. I might add this later.

import socketserver
import threading
import time

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class RequestHandler(socketserver.BaseRequestHandler):

    def __init__(self, callback, *args, **keys):
        # callback is a function which accepts a query and a request controller
        self.callback = callback
        socketserver.BaseRequestHandler.__init__(self, *args, **keys)

    # Handle a request and stick the query into the queue.
    def handle(self):
        # We use a newline character as terminator for our input
        # This means every query needs to be terminated by a newline!
        query = ''
        success = True
        while query == '' or query[len(query) - 1] != '\n':
            data = self.request.recv(1024)
            
            # Connection might be terminated early by client
            if not data:
                success = False
                break

            query += str(data, 'UTF-8')


        # Only send something to maxima if we received a full request
        if success:
            # Controller object which is passed to the 
            # TODO: It would be a lot easier to pass on the tcp client (request) itself
            # But at the moment this feels cleaner.
            controller = RequestController() 
            self.callback(query, controller)
            
            # Wait for a Maxima worker thread to process our input 
            controller.wait()

            reply = controller.get_reply()
            if reply:
                self.request.sendall(bytes(controller.get_reply(), 'UTF-8'))
            del controller
            
        self.request.close()


class RequestController:
    """ RequestController are used to exchange data
    between the TCP server and the maxima worker threads
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

    def wait(self):
        self.ready.wait()

    def set_reply(self, reply):
        self.reply = reply

    def get_reply(self):
        return self.reply
