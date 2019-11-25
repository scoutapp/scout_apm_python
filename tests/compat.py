# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

try:
    from unittest import mock
except ImportError:
    # Python 2
    import mock

try:
    from tempfile import TemporaryDirectory
except ImportError:  # Python < 3.2
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

__all__ = ["mock", "TemporaryDirectory"]
