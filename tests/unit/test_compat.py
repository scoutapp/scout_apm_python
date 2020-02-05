# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import functools
import sys

import pytest

from scout_apm.compat import (
    ContextDecorator,
    datetime_to_timestamp,
    get_pos_args,
    text,
    unwrap_decorators,
)


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


def test_get_pos_args_args():
    def foo(bar, baz):
        pass

    assert get_pos_args(foo) == ["bar", "baz"]


def test_get_pos_args_kwargs():
    def foo(bar, baz=None):
        pass

    assert get_pos_args(foo) == ["bar", "baz"]


def test_unwrap_decorators_no_decorators():
    def foo():
        pass

    assert unwrap_decorators(foo) is foo


def test_unwrap_decorators_one_decorator():
    def foo():
        pass

    @functools.wraps(foo)
    def bar():
        return foo()

    if sys.version_info < (3,):
        bar.__wrapped__ = foo

    assert unwrap_decorators(bar) is foo
