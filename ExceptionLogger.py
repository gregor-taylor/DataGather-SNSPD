import logging
import sys

class exception_logger(object):
    def __init__(self, logfile):
        self.FORMAT = '%(asctime)-15s %(message)s'
        self.log_file = logfile
        logging.basicConfig(filename=self.log_file, format=self.FORMAT)
        self.logger = logging.getLogger('ErrorLogger')
        sys.excepthook = self.log_handler

    def log_handler(self, type, value, tb):
	    self.logger.exception("Uncaught exception: {0}".format(str(value))+'\n'+str(tb))

