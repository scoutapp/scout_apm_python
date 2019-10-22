# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import time

from scout_apm.compat import datetime_to_timestamp, urlencode
from scout_apm.core.context import AgentContext

# Originally derived from:
# 1. Rails:
#   https://github.com/rails/rails/blob/0196551e6039ca864d1eee1e01819fcae12c1dc9/railties/lib/rails/generators/rails/app/templates/config/initializers/filter_parameter_logging.rb.tt
# 2. Sentry server side scrubbing:
#   https://docs.sentry.io/data-management/sensitive-data/#server-side-scrubbing
FILTER_PARAMETERS = frozenset(
    [
        "access",
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "auth_token",
        "card[number]",
        "certificate",
        "credentials",
        "crypt",
        "key",
        "mysql_pwd",
        "otp",
        "passwd",
        "password",
        "private",
        "protected",
        "salt",
        "secret",
        "ssn",
        "stripetoken",
        "token",
    ]
)


def create_filtered_path(path, query_params):
    if AgentContext.instance.config.value("uri_reporting") == "path":
        return path
    filtered_params = sorted(
        (
            (k, "[FILTERED]" if k.lower() in FILTER_PARAMETERS else v)
            for k, v in query_params
        )
    )
    if not filtered_params:
        return path
    return path + "?" + urlencode(filtered_params)


def ignore_path(path):
    ignored_paths = AgentContext.instance.config.value("ignore")
    for ignored in ignored_paths:
        if path.startswith(ignored):
            return True
    return False


def track_request_queue_time(header_value, tracked_request):
    if header_value.startswith("t="):
        header_value = header_value[2:]

    try:
        first_char = header_value[0]
    except IndexError:
        return False

    if not first_char.isdigit():  # filter out negatives, nan, inf, etc.
        return False

    try:
        ambiguous_start_timestamp = float(header_value)
    except ValueError:
        return False

    start_timestamp_ns = convert_ambiguous_timestamp_to_ns(ambiguous_start_timestamp)
    if start_timestamp_ns == 0.0:
        return False

    tr_start_timestamp_ns = datetime_to_timestamp(tracked_request.start_time) * 1e9

    # Ignore if in the future
    if start_timestamp_ns > tr_start_timestamp_ns:
        return False

    queue_time_ns = int(tr_start_timestamp_ns - start_timestamp_ns)
    tracked_request.tag("scout.queue_time_ns", queue_time_ns)
    return True


def track_amazon_request_queue_time(header_value, tracked_request):
    items = header_value.split(";")
    found_item = None
    for item in items:
        if found_item is None and item.startswith("Root="):
            found_item = item
        elif item.startswith("Self="):
            found_item = item

    if found_item is None:
        return False

    pieces = found_item.split("-")
    if len(pieces) != 3:
        return False

    timestamp_str = pieces[1]

    try:
        first_char = timestamp_str[0]
    except IndexError:
        return False

    if not first_char.isdigit():
        return False

    try:
        start_timestamp_ns = int(timestamp_str) * 1000000000.0
    except ValueError:
        return False

    if start_timestamp_ns == 0:
        return False

    tr_start_timestamp_ns = datetime_to_timestamp(tracked_request.start_time) * 1e9

    # Ignore if in the futuren
    if start_timestamp_ns > tr_start_timestamp_ns:
        return False

    queue_time_ns = int(tr_start_timestamp_ns - start_timestamp_ns)
    tracked_request.tag("scout.queue_time_ns", queue_time_ns)
    return True


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
