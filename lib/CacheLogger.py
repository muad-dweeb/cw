from datetime import datetime
import inspect
import logging


class CacheLogger(object):

    """
    Wrapper for standard logger functionality that preserves a cache of recently logged messages, like a Tail
    This cache can be retrieved for reporting.
    """

    def __init__(self, caller, cache_limit, debug=False):
        self._caller = caller
        self._debug = debug
        self._logger = self._create_logger()
        self._cache_limit = cache_limit
        self.cache = list()

    def _create_logger(self):
        """ General purpose logger with simple configuration """
        if self._debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        new_logger = logging.getLogger(self._caller)
        console_handler = logging.StreamHandler()
        log_format = logging.Formatter('%(asctime)s - %(caller)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(log_format)
        new_logger.addHandler(console_handler)
        new_logger.setLevel(log_level)
        # Prevent duplicate log entries if another handler exists downstream:
        #    https://stackoverflow.com/a/44426266/3900915
        new_logger.propagate = False
        return new_logger

    def _prune_cache(self):
        if len(self.cache) > self._cache_limit:
            del self.cache[0]

    @staticmethod
    def _augment_message(message, level):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return '{} - {} - {}'.format(now, level, message)

    def info(self, message):
        caller = inspect.stack()[1].function
        cache_message = self._augment_message(message, 'INFO')
        self._logger.info(message, extra={'caller': caller})
        self.cache.append(cache_message)
        self._prune_cache()

    def debug(self, message):
        caller = inspect.stack()[1].function
        cache_message = self._augment_message(message, 'DEBUG')
        self._logger.debug(message, extra={'caller': caller})
        self.cache.append(cache_message)
        self._prune_cache()

    def warning(self, message):
        caller = inspect.stack()[1].function
        cache_message = self._augment_message(message, 'WARNING')
        self._logger.warning(message, extra={'caller': caller})
        self.cache.append(cache_message)
        self._prune_cache()

    def error(self, message):
        caller = inspect.stack()[1].function
        cache_message = self._augment_message(message, 'ERROR')
        self._logger.error(message, extra={'caller': caller})
        self.cache.append(cache_message)
        self._prune_cache()

    def exception(self, message):
        caller = inspect.stack()[1].function
        cache_message = self._augment_message(message, 'EXCEPTION')
        self._logger.exception(message, extra={'caller': caller})
        self.cache.append(cache_message)
        self._prune_cache()

    def append_stack_trace(self, stack_trace_string):
        stack_trace_string = stack_trace_string.split('\n')
        self.cache.extend(stack_trace_string)
