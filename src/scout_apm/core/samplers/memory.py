import logging
import psutil

# Logging
logger = logging.getLogger(__name__)


class Memory(object):
    @staticmethod
    def rss_to_mb(rss_in_bytes):
        """
        Convert a number of bytes to a number of megabytes.
        """
        bytes_per_kb = 1024
        kb_per_megabyte = 1024
        return float(rss_in_bytes) / bytes_per_kb / kb_per_megabyte

    @staticmethod
    def rss():
        """
        Returns the memory usage (RSS) of this process, in bytes
        """
        return psutil.Process().memory_info().rss

    @staticmethod
    def rss_in_mb():
        return Memory.rss_to_mb(Memory.rss())

    def metric_type(self):
        return 'Memory'

    def metric_name(self):
        return 'Physical'

    def human_name(self):
        return 'Process Memory'

    def run(self):
        res = self.__class__.rss_in_mb()
        logger.debug('{human_name}: #{res}'.format(
            human_name=self.human_name(),
            res=res))
        return res
