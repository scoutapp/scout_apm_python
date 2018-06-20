from __future__ import absolute_import

import logging

# Logging
logger = logging.getLogger(__name__)


class NPlusOneCallSet():
    def __init__(self):
        self.items = {}

    def update(self, sql_string, call_count, call_duration):
        self.find_for(sql_string).update(call_count, call_duration)

    def should_capture_backtrace(self, sql_string):
        return self.find_for(sql_string).should_capture_backtrace()

    def find_for(self, sql_string):
        if sql_string not in self.items:
            self.items[sql_string] = NPlusOneCallSetItem(sql_string)
        return self.items[sql_string]


class NPlusOneCallSetItem():
    # Fetch backtraces on this number of same SQL calls
    CALL_COUNT_THRESHOLD = 5

    # Minimum time in seconds before we start performing any work.
    DURATION_THRESHOLD = 150/1000.0

    def __init__(self, sql_string):
        self.sql_string = sql_string
        self.captured = False
        self.call_count = 0
        self.call_duration = 0.0  # In Seconds
        self.past_duration_threshold = False

    def update(self, call_count, call_duration):
        if self.captured is True:
            # No need to do any work if we've already captured a backtrace.
            return
        self.call_count += call_count
        self.call_duration += call_duration

    def is_past_duration_threshold(self):
        if self.past_duration_threshold is True:
            # no need to check again once past
            return True
        self.past_duration_threshold = self.call_duration >= self.__class__.DURATION_THRESHOLD
        return self.past_duration_threshold

    # Call count and call duration must both be past thresholds.
    def should_capture_backtrace(self):
        if (not self.captured) and (self.call_count >= self.__class__.CALL_COUNT_THRESHOLD) and self.is_past_duration_threshold():
            self.captured = True
            return True
        return False
