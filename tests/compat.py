# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import gzip
import sys

if sys.version_info >= (3, 0):
    from types import SimpleNamespace
else:

    class SimpleNamespace(object):
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


if sys.version_info >= (3, 0):
    from unittest import mock
else:
    import mock

if sys.version_info >= (3, 2):
    from tempfile import TemporaryDirectory
else:
    from contextlib import contextmanager
    from shutil import rmtree
    from tempfile import mkdtemp

    @contextmanager
    def TemporaryDirectory(*args, **kwargs):
        tempdir = mkdtemp(*args, **kwargs)
        try:
            yield tempdir
        finally:
            rmtree(tempdir)


if sys.version_info >= (3, 7):
    from contextlib import nullcontext
else:
    from contextlib import contextmanager

    @contextmanager
    def nullcontext(obj):
        yield obj


if sys.version_info >= (3, 4):
    from contextlib import suppress
else:
    from contextlib import contextmanager

    @contextmanager
    def suppress(*exceptions):
        try:
            yield
        except exceptions:
            pass


if sys.version_info >= (3, 2):

    def gzip_decompress(data):
        return gzip.decompress(data)


else:
    import io

    def gzip_decompress(data):
        """Reimplementation gzip.compress for python 2.7"""
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as f:
            return f.read()


try:
    from contextvars import copy_context
except ImportError:
    copy_context = None


__all__ = [
    "gzip_decompress",
    "mock",
    "nullcontext",
    "suppress",
    "TemporaryDirectory",
    "copy_context",
]
