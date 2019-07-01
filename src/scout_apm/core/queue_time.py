# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import time

from scout_apm.compat import datetime_to_timestamp


def track_request_queue_time(header_value, tracked_request):
    if header_value.startswith("t="):
        header_value = header_value[2:]

    try:
        first_char = header_value[0]
    except IndexError:
        return

    if not first_char.isdigit():  # filter out negatives, nan, inf, etc.
        return

    try:
        ambiguous_start_timestamp = float(header_value)
    except ValueError:
        return

    start_timestamp_ns = convert_ambiguous_timestamp_to_ns(ambiguous_start_timestamp)
    if start_timestamp_ns == 0.0:
        return

    tr_start_timestamp_ns = datetime_to_timestamp(tracked_request.start_time) * 1e9

    # Ignore if in the future
    if start_timestamp_ns > tr_start_timestamp_ns:
        return

    queue_time_ns = int(tr_start_timestamp_ns - start_timestamp_ns)
    tracked_request.tag("scout.queue_time_ns", queue_time_ns)


# Cutoff epoch is used for determining ambiguous timestamp boundaries, and is
# just over 10 years ago at time of writing
CUTOFF_EPOCH_S = time.mktime((2009, 6, 1, 0, 0, 0, 0, 0, 0))
CUTOFF_EPOCH_MS = CUTOFF_EPOCH_S * 1000.0
CUTOFF_EPOCH_US = CUTOFF_EPOCH_S * 1000000.0
CUTOFF_EPOCH_NS = CUTOFF_EPOCH_S * 1000000000.0


def convert_ambiguous_timestamp_to_ns(timestamp):
    """
    Convert an ambiguous float timestamp that could be in nanoseconds,
    microseconds, milliseconds, or seconds to nanoseconds. Return 0.0 for
    values in the more than 10 years ago.
    """
    if timestamp > CUTOFF_EPOCH_NS:
        converted_timestamp = timestamp
    elif timestamp > CUTOFF_EPOCH_US:
        converted_timestamp = timestamp * 1000.0
    elif timestamp > CUTOFF_EPOCH_MS:
        converted_timestamp = timestamp * 1000000.0
    elif timestamp > CUTOFF_EPOCH_S:
        converted_timestamp = timestamp * 1000000000.0
    else:
        return 0.0
    return converted_timestamp
