import unittest
import configparser
import logging
from queue import Queue

from maxima_threads import MaximaWorker
from maxima_threads import RequestController
from config_loader import Config


class MaximaWorkerTests(unittest.TestCase):

    def setUp(self):
        config = Config()
        # I only need the logger if tests fail...
        # logging.basicConfig(level=config['General']['loglevel'])
        # self.logger = logging.getLogger("tcp2maxima")

        self.queries = Queue()
        self.worker = MaximaWorker('testWorker', self.queries, config['Maxima'])
        self.worker.start()

    def tearDown(self):
        self.worker.quit_worker()

    def testMaximaReply(self):
        controller = RequestController('12+12;')
        self.queries.put(controller)
        controller.wait()
        reply = controller.get_reply()
        self.assertTrue(reply == '24')

    def testTimeout(self):
        # We send a incomplete query without a ; - this should
        # give us a timeout.
        controller = RequestController('12+12')
        self.queries.put(controller)
        controller.wait()
        reply = controller.get_reply()
        self.assertTrue(reply == ';ERR;TIMEOUT')

    def testNoOutput(self):
        controller = RequestController(';')
        self.queries.put(controller)
        controller.wait()
        reply = controller.get_reply()
        self.assertTrue(reply == ';ERR;NO_OUTPUT')

    def testBurst(self):
        controllers = []
        for i in range(100):
            controllers.append(RequestController('2^3;'))

        for req in controllers:
            self.queries.put(req)

        for rep in controllers:
            rep.wait()
            reply = rep.get_reply()
            self.assertTrue(reply == '8')

    def testBurstTimeout(self):
        controllers = []
        for i in range(10):
            controllers.append(RequestController('12^12^12^12;'))

        for req in controllers:
            self.queries.put(req)

        for rep in controllers:
            rep.wait()
            reply = rep.get_reply()
            self.assertTrue(reply == ';ERR;TIMEOUT')

def main():
    unittest.main()

if __name__ == '__main__':
    main()
