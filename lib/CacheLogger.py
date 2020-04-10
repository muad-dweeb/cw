from datetime import datetime


class CacheLogger(object):

    """
    Wrapper for standard logger functionality that preserves a cache of recently logged messages, like a Tail
    This cache can be retrieved for reporting.
    """

    def __init__(self, logger, cache_limit):
        self._logger = logger
        self._cache_limit = cache_limit
        self.cache = list()

    def _prune_cache(self):
        if len(self.cache) > self._cache_limit:
            del self.cache[0]

    @staticmethod
    def _augment_message(message, level):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return '{} - {} - {}'.format(now, level, message)

    def info(self, message):
        cache_message = self._augment_message(message, 'INFO')
        self._logger.info(message)
        self.cache.append(cache_message)
        self._prune_cache()

    def debug(self, message):
        cache_message = self._augment_message(message, 'DEBUG')
        self._logger.debug(message)
        self.cache.append(cache_message)
        self._prune_cache()

    def warning(self, message):
        cache_message = self._augment_message(message, 'WARNING')
        self._logger.warning(message)
        self.cache.append(cache_message)
        self._prune_cache()

    def error(self, message):
        cache_message = self._augment_message(message, 'ERROR')
        self._logger.error(message)
        self.cache.append(cache_message)
        self._prune_cache()

    def exception(self, message):
        cache_message = self._augment_message(message, 'EXCEPTION')
        self._logger.exception(message)
        self.cache.append(cache_message)
        self._prune_cache()

    def append_stack_trace(self, stack_trace_string):
        stack_trace_string = stack_trace_string.split('\n')
        self.cache.extend(stack_trace_string)
