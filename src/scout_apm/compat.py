# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import inspect
import sys
from functools import wraps

import certifi
import urllib3

string_type = str if sys.version_info[0] >= 3 else basestring  # noqa: F821
text_type = str if sys.version_info[0] >= 3 else unicode  # noqa: F821
string_types = tuple({string_type, text_type})

if sys.version_info >= (3,):

    def iteritems(dictionary):
        return dictionary.items()


else:

    def iteritems(dictionary):
        return dictionary.iteritems()  # noqa: B301


if sys.version_info >= (3, 2):
    from contextlib import ContextDecorator
else:
    import functools

    class ContextDecorator(object):
        def __call__(self, f):
            @functools.wraps(f)
            def decorated(*args, **kwds):
                with self:
                    return f(*args, **kwds)

            return decorated


if sys.version_info >= (3, 0):
    import queue
else:
    import Queue as queue

# datetime_to_timestamp converts a naive UTC datetime to a unix timestamp
if sys.version_info >= (3, 3):

    def datetime_to_timestamp(datetime_obj):
        return datetime_obj.replace(tzinfo=dt.timezone.utc).timestamp()


else:
    _EPOCH = dt.datetime(1970, 1, 1)

    def datetime_to_timestamp(datetime_obj):
        return (datetime_obj - _EPOCH).total_seconds()


def text(value, encoding="utf-8", errors="strict"):
    """
    Convert a value to str on Python 3 and unicode on Python 2.
    """
    if isinstance(value, text_type):
        return value
    elif isinstance(value, bytes):
        return text_type(value, encoding, errors)
    else:
        return text_type(value)


if sys.version_info >= (3, 0):
    from urllib.parse import parse_qsl, urlencode
else:
    from urllib import urlencode

    from urlparse import parse_qsl


if sys.version_info >= (3, 0):

    def get_pos_args(func):
        return inspect.getfullargspec(func).args


else:

    def get_pos_args(func):
        return inspect.getargspec(func).args


def unwrap_decorators(func):
    unwrapped = func
    while True:
        # N.B. only some decorators set __wrapped__ on Python 2.7
        try:
            unwrapped = unwrapped.__wrapped__
        except AttributeError:
            break
    return unwrapped


def kwargs_only(func):
    """
    Source: https://pypi.org/project/kwargs-only/
    Make a function only accept keyword arguments.
    This can be dropped in Python 3 in lieu of:
        def foo(*, bar=default):
    Source: https://pypi.org/project/kwargs-only/
    """
    if hasattr(inspect, "signature"):  # pragma: no cover
        # Python 3
        signature = inspect.signature(func)
        arg_names = list(signature.parameters.keys())
    else:  # pragma: no cover
        # Python 2
        signature = inspect.getargspec(func)
        arg_names = signature.args

    if len(arg_names) > 0 and arg_names[0] in ("self", "cls"):
        allowable_args = 1
    else:
        allowable_args = 0

    @wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > allowable_args:
            raise TypeError(
                "{} should only be called with keyword args".format(func.__name__)
            )
        return func(*args, **kwargs)

    return wrapper


def urllib3_cert_pool_manager(**kwargs):
    if sys.version_info >= (3, 0):
        CERT_REQUIRED = "CERT_REQUIRED"
    else:
        CERT_REQUIRED = b"CERT_REQUIRED"
    return urllib3.PoolManager(cert_reqs=CERT_REQUIRED, ca_certs=certifi.where())


__all__ = [
    "ContextDecorator",
    "datetime_to_timestamp",
    "kwargs_only",
    "parse_qsl",
    "queue",
    "string_type",
    "text",
    "text_type",
    "urlencode",
]
