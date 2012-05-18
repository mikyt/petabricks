import logging


class NonRootFilter:
    "Allows everything not coming from the root logger itself to be logged"
    def filter(self, record):
        """The function implementing the filter"""
        if record.name == "root":
            # Don't log
            return 0
        return 1


def configureLogging(errorfile):
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)
    rootLogger.addFilter(NonRootFilter())

    # create file handler which logs error messages
    fh = logging.FileHandler(errorfile, mode="w")
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                  '%(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # add the handlers to logger
    rootLogger.addHandler(fh)
