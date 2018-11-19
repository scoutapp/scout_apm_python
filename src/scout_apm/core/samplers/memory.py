from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import psutil

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

    @staticmethod
    def get_delta(prior_rss_in_mb):
        mem = Memory.rss_in_mb()
        if mem > prior_rss_in_mb:
            return mem - prior_rss_in_mb
        return 0.0

    def metric_type(self):
        return "Memory"

    def metric_name(self):
        return "Physical"

    def human_name(self):
        return "Process Memory"

    def run(self):
        res = self.__class__.rss_in_mb()
        logger.debug("%s: #%s", self.human_name(), res)
        return res
