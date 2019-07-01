# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt

import pytest

from scout_apm.compat import datetime_to_timestamp
from scout_apm.core.queue_time import track_request_queue_time


@pytest.mark.parametrize("with_t", [True, False])
def test_track_request_queue_time_valid(with_t, tracked_request):
    queue_start = int(datetime_to_timestamp(dt.datetime.utcnow()) - 2)
    if with_t:
        header_value = str("t=") + str(queue_start)
    else:
        header_value = str(queue_start)

    track_request_queue_time(header_value, tracked_request)
    queue_time_ns = tracked_request.tags["scout.queue_time_ns"]
    # Upper bound assumes we didn't take more than 2s to run this test...
    assert queue_time_ns >= 2000000000 and queue_time_ns < 4000000000


@pytest.mark.parametrize(
    "header_value",
    [
        str(""),
        str("t=X"),  # first character not a digit
        str("t=0.3f"),  # raises ValueError on float() conversion
        str(datetime_to_timestamp(dt.datetime.utcnow()) + 3600.0),  # one hour in future
        str(datetime_to_timestamp(dt.datetime(2009, 1, 1))),  # before ambig cutoff
    ],
)
def test_track_request_queue_time_invalid(header_value, tracked_request):
    track_request_queue_time(header_value, tracked_request)

    assert "scout.queue_time_ns" not in tracked_request.tags
