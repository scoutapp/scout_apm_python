# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import time

from scout_apm.compat import datetime_to_timestamp, parse_qsl, text_type, urlencode
from scout_apm.core.config import scout_config

# Originally derived from:
# 1. Rails:
#   https://github.com/rails/rails/blob/0196551e6039ca864d1eee1e01819fcae12c1dc9/railties/lib/rails/generators/rails/app/templates/config/initializers/filter_parameter_logging.rb.tt  # noqa
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
    if scout_config.value("uri_reporting") == "path":
        return path
    # We expect query_params to have keys and values both of strings, because
    # that's how frameworks build it. However sometimes application code
    # mutates this structure to use incorrect types before we read it, so we
    # have to cautiously make everything a string again. Ignoring the
    # possibilities of bytes or objects with bad __str__ methods because they
    # seem very unlikely.
    string_query_params = (
        (text_type(key), text_type(value)) for key, value in query_params
    )
    # Python 2 unicode compatibility: force all keys and values to bytes
    filtered_params = sorted(
        (
            (
                key.encode("utf-8"),
                (
                    b"[FILTERED]"
                    if key.lower() in FILTER_PARAMETERS
                    else value.encode("utf-8")
                ),
            )
            for key, value in string_query_params
        )
    )
    if not filtered_params:
        return path
    return path + "?" + urlencode(filtered_params)


def ignore_path(path):
    ignored_paths = scout_config.value("ignore")
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


# Cutoff epoch is used for determining ambiguous timestamp boundaries
CUTOFF_EPOCH_S = time.mktime((dt.date.today().year - 10, 1, 1, 0, 0, 0, 0, 0, 0))
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


def asgi_track_request_data(scope, tracked_request):
    """
    Track request data from an ASGI HTTP or Websocket scope.
    """
    path = scope.get("root_path", "") + scope["path"]
    query_params = parse_qsl(scope.get("query_string", b"").decode("utf-8"))
    tracked_request.tag("path", create_filtered_path(path, query_params))
    if ignore_path(path):
        tracked_request.tag("ignore_transaction", True)

    # We only care about the last values of headers so don't care that we use
    # a plain dict rather than a multi-value dict
    headers = {k.lower(): v for k, v in scope.get("headers", ())}

    if scout_config.value("collect_remote_ip"):
        user_ip = (
            headers.get(b"x-forwarded-for", b"").decode("latin1").split(",")[0]
            or headers.get(b"client-ip", b"").decode("latin1").split(",")[0]
            or scope.get("client", ("",))[0]
        )
        tracked_request.tag("user_ip", user_ip)

    queue_time = headers.get(b"x-queue-start", b"") or headers.get(
        b"x-request-start", b""
    )
    tracked_queue_time = track_request_queue_time(
        queue_time.decode("latin1"), tracked_request
    )
    if not tracked_queue_time:
        amazon_queue_time = headers.get(b"x-amzn-trace-id", b"")
        track_amazon_request_queue_time(
            amazon_queue_time.decode("latin1"), tracked_request
        )


def werkzeug_track_request_data(werkzeug_request, tracked_request):
    """
    Several integrations use Werkzeug requests, so share the code for
    extracting common data here.
    """
    path = werkzeug_request.path
    tracked_request.tag(
        "path", create_filtered_path(path, werkzeug_request.args.items(multi=True))
    )
    if ignore_path(path):
        tracked_request.tag("ignore_transaction", True)

    if scout_config.value("collect_remote_ip"):
        # Determine a remote IP to associate with the request. The value is
        # spoofable by the requester so this is not suitable to use in any
        # security sensitive context.
        user_ip = (
            werkzeug_request.headers.get("x-forwarded-for", default="").split(",")[0]
            or werkzeug_request.headers.get("client-ip", default="").split(",")[0]
            or werkzeug_request.remote_addr
        )
        tracked_request.tag("user_ip", user_ip)

    queue_time = werkzeug_request.headers.get(
        "x-queue-start", default=""
    ) or werkzeug_request.headers.get("x-request-start", default="")
    tracked_queue_time = track_request_queue_time(queue_time, tracked_request)
    if not tracked_queue_time:
        amazon_queue_time = werkzeug_request.headers.get("x-amzn-trace-id", default="")
        track_amazon_request_queue_time(amazon_queue_time, tracked_request)
