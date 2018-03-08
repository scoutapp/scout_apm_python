import logging
import platform
import resource

# Logging
logger = logging.getLogger(__name__)


class Memory(object):
    # Account for Darwin returning maxrss in bytes and Linux in KB. Used by
    # the slow converters. Doesn't feel like this should go here
    # though...more of a utility.
    @staticmethod
    def rss_to_mb(rss):
        kilobyte_adjust = 1024 if (platform.system == 'Darwin') else 1
        return float(rss) / 1024 / kilobyte_adjust

    @staticmethod
    def rss():
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    @staticmethod
    def rss_in_mb():
        return Memory.rss_to_mb(Memory.rss())

    def metric_type(self):
        return 'Memory'

    def metric_name(self):
        return 'Physical'

    def human_name(self):
        return 'Process Memory'

    def metrics(self):
        """
        TODO: after implementing metrics collector,
        make sure this returns compatible metrics
        """
        return None

    def run(self):
        res = self.__class__.rss_in_mb()
        logger.debug('{human_name}: #{res}'.format(
            human_name=self.human_name(),
            res=res))
        return res
