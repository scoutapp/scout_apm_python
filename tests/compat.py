# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

if sys.version_info >= (3, 0):
    import mock
else:
    from unittest import mock

if sys.version_info >= (3, 2):
    from tempfile import TemporaryDirectory
else:
    from contextlib import contextmanager
    from tempfile import mkdtemp
    from shutil import rmtree

    @contextmanager
    def TemporaryDirectory():
        tempdir = mkdtemp()
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


__all__ = ["mock", "nullcontext", "TemporaryDirectory"]
