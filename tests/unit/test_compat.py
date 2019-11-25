# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt

import pytest

from scout_apm.compat import ContextDecorator, datetime_to_timestamp, text


def test_context_decorator():
    class MyCD(ContextDecorator):
        def __init__(self):
            self.called = False

        def __enter__(self):
            self.called = True

        def __exit__(self, *exc):
            pass

    my_cd = MyCD()

    @my_cd
    def example():
        pass

    example()

    assert my_cd.called


@pytest.mark.parametrize(
    "given, expected",
    [
        (dt.datetime(1970, 1, 1), 0),
        (dt.datetime(1970, 1, 1, 1), 3600.0),
        (dt.datetime(1970, 1, 1, 0, 30), 1800.0),
        (dt.datetime(2019, 7, 2, 9, 23, 41), 1562059421.0),
    ],
)
def test_datetime_to_timestamp(given, expected):
    assert datetime_to_timestamp(given) == expected


@pytest.mark.parametrize(
    "given, expected", [("foo", "foo"), (b"foo", "foo"), ([], "[]")]
)
def test_text(given, expected):
    assert text(given) == expected
