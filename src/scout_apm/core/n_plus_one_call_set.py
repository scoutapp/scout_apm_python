# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict


class NPlusOneCallSet(defaultdict):
    def __init__(self):
        # Force no arguments
        super(NPlusOneCallSet, self).__init__()

    def __missing__(self, key):
        return NPlusOneCallSetItem(key)


class NPlusOneCallSetItem(object):
    # Fetch backtraces on this number of same SQL calls
    CALL_COUNT_THRESHOLD = 5

    # Minimum time in seconds before we start performing any work.
    DURATION_THRESHOLD = 0.150

    def __init__(self, sql_string):
        self.sql_string = sql_string
        self.captured = False
        self.call_count = 0
        self.call_duration = 0.0  # In Seconds

    def add(self, call_duration, call_count=1):
        if self.captured:
            # No need to do any work if we've already captured a backtrace.
            return
        self.call_count += call_count
        self.call_duration += call_duration

    def should_capture_backtrace(self):
        if self.captured:
            return False
        # Call count and call duration must both be past thresholds.
        if (
            self.call_count >= self.CALL_COUNT_THRESHOLD
            and self.call_duration >= self.DURATION_THRESHOLD
        ):
            self.captured = True
            return True
        return False
