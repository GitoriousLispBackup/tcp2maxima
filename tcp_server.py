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

    # We use a RequestController object to talk to the Maxima
    # threads. This is probably not the best way to do this
    # and might even be agains good programming principles
    # or common sense. But I had no better idea.
    def handle(self):
        query = str(self.request.recv(1024), 'UTF-8')
        # Yes, that's the stupid part
        controller = RequestController() 
        self.callback(query, controller)
        
        # Wait for a Maxima worker thread to process our input 
        controller.wait()

        self.request.sendall(bytes(controller.get_reply(), 'UTF-8'))
        del controller

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

    def wait(self):
        self.ready.wait()

    def set_reply(self, reply):
        self.reply = reply

    def get_reply(self):
        return self.reply
