import logging

# logging.basicConfig(level=logging.CRITICAL, format='%(filename)s (%(lineno)d): %(funcName)s: %(message)s')
dlogger: logging.Logger = logging.getLogger("denc_logger")

# Enable this to debug imports
import sys
dlogger.addHandler(logging.StreamHandler(sys.stdout))
dlogger.setLevel(logging.WARNING)
