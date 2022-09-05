import logging
import sys
import threading
from pathlib import Path
from typing import Optional

__instance = None
__handlers = []
__uninitialized_loggers = []


class ExitOnExceptionHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord):
        if record.levelno in (logging.CRITICAL,):
            # do not remove as other parts of the codebase rely on this
            logging.shutdown()
            raise SystemExit(-1)


class SynchronizedStreamHandler(logging.StreamHandler):

    __current_stream = None
    __lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        handler = SynchronizedStreamHandler
        with self.__lock:
            if self.stream != handler.__current_stream and handler.__current_stream is not None:
                handler.__current_stream.flush()
            handler.__current_stream = self.stream
            super().emit(record)


def get_logger(context: str) -> logging.Logger:
    logger = logging.getLogger(context)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if __instance is None:
        __uninitialized_loggers.append(logger)
    else:
        for h in __handlers:
             logger.addHandler(h)
    
    return logger


def init_global_logging(log_file: Optional[Path], file_logging_level:int=logging.INFO, console_logging_level:int=logging.WARNING):
    global __handlers, __instance
    if __instance is not None:
        raise RuntimeError("Global logging already initialized")

    __instance = 1

    formatter_file = logging.Formatter(fmt='[%(levelname)s] [%(name)s:%(lineno)d] %(message)s')
    formatter_ch_stdout = logging.Formatter(fmt='[%(levelname)s] [%(name)s] %(message)s')
    formatter_ch_stderr = logging.Formatter(fmt='[%(levelname)s] [%(name)s:%(lineno)d] %(message)s')

    ch_out = SynchronizedStreamHandler(stream=sys.stdout)
    ch_out.setLevel(console_logging_level)
    ch_out.setFormatter(formatter_ch_stdout)
    ch_out.addFilter(lambda record: record.levelno <= logging.INFO)

    ch_err = SynchronizedStreamHandler(stream=sys.stderr)
    ch_err.setLevel(logging.WARNING)
    ch_err.setFormatter(formatter_ch_stderr)

    __handlers.append(ch_out)
    __handlers.append(ch_err)

    if log_file is not None:
        fh = logging.FileHandler(log_file)
        fh.setLevel(file_logging_level)
        fh.setFormatter(formatter_file)

        __handlers.append(fh)

    # do not remove as other parts of the codebase rely on this
    ext = ExitOnExceptionHandler()
    ext.setFormatter(formatter_ch_stderr)
    __handlers.append(ext)

    root = logging.getLogger()
    # do not remove as other parts of the codebase rely on this
    root.addHandler(ext)

    while len(__uninitialized_loggers) > 0:
        logger = __uninitialized_loggers.pop()
        
        for h in __handlers:
            logger.addHandler(h)
    