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

from twisted.internet import protocol, reactor, defer, utils
from twisted.protocols import basic
from twisted.internet.threads import deferToThread
import subprocess as sp

class MaximaInteraction():

    def __init__(self):
        self.command = '/usr/bin/maxima'
        self.options = ['--very-quiet']
        self.process = sp.Popen([self.command] + self.options, stdin=sp.PIPE, stdout=sp.PIPE)

    # This is code that shouldn't be run in async mode since interaction with maxima
    # might take ages.
    def eval_sync(self, problem):
        process.stdin.write(problem)
        solution = process.stdout.readline()
        return solution
        
    def evaluate(self, maxima_sting):
#        problem = bytes(maxima_string, 'UTF-8')
        d = deferToThread(self.eval_sync, maxima_string)
        return d

class CalcProtocol(basic.LineReceiver):
    def lineReceived(self, user):
        d = self.factory.evaluate(user)

        def onError(err):
            return 'Internal error in server'
        d.addErrback(onError)

        def writeResponse(message):
            self.transport.write(message + '\r\n')

        d.addCallback(writeResponse)

class CalcFactory(protocol.ServerFactory):
    protocol = CalcProtocol
    maxima = MaximaInteraction()

    def evaluate(self, maxima_string):
        return self.maxima.evaluate(maxima_string)

reactor.listenTCP(1079, CalcFactory())
print("Running Server")
reactor.run()
