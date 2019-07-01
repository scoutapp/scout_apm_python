# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.compat import datetime_to_timestamp
from scout_apm.core.util import convert_ambiguous_timestamp_to_ns


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
