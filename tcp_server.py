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

# TODO: Make this work in one way or another.

import socketserver
from maxima_threads import MaximaSupervisor

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class RequestHandler(socketserver.BaseRequestHandler):

    # This doesn't work at the moment. I guess it's because it's 
    # was a stupid idea in the first place which abuses threads
    # in a way you are not supposed to!
    def handle(self):
        query = str(self.request.recv(1024), 'UTF-8')
        # Yes, that's the stupid part
        callback = lambda x: self.request.sendall(bytes(x, 'UTF-8'))
        self.server.maxima.request(query, callback)


# Should not be executed in the end
# but I have to test it, aight?
def main():
    host, port = "localhost", 9666 # My favourite port of the beast
    supervisor = MaximaSupervisor()
    supervisor.start()
    server = ThreadedTCPServer((host, port), RequestHandler)
    # Ugly hack to check whether this works 
    server.maxima = supervisor
    server.serve_forever()

    supervisor.quit()
    supervisor.join()


if __name__ == "__main__":
    main()
