import unittest
import configparser
from ... import maxima_worker
from queue import Queue


class MaximaWorkerTests(unittest.TestCase):

    def setUp(self):
        config = configparser.ConfigParser()
        config.readfp(open('../default.cfg'))
        self.queries = Queue()
        self.worker = MaximaWorker('testWorker', config['Maxima'])

    def tearDown(self):
        self.worker.quit_worker()

    def testMaximaReply(self):
        request_contr = RequestController()
        request = '12+12;'
        self.queries.put((request, request_contr))
        controller.wait()
        reply = controller.get_reply()
        self.failUnless(reply == '24')

    def testTimeout(self):
        self.failUnless(False)

def main():
    unittest.main()

if __name__ == '__main__':
    main()
