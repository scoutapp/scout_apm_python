# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from scout_apm.core import backtrace


def test_capture():
    stack = backtrace.capture()

    assert isinstance(stack, list)
    assert len(stack) >= 1
    for frame in stack:
        assert isinstance(frame, dict)
        assert set(frame.keys()) == {"file", "line", "function"}
        assert isinstance(frame["file"], str)
        assert isinstance(frame["line"], int)
        assert isinstance(frame["function"], str)

    assert stack[0]["file"] == format_py_filename(__file__)


def format_py_filename(filename):
    if sys.version_info[0] == 2 and filename.endswith(".pyc"):
        # Python 2 will include .pyc filename if it's used, so strip that
        return filename[:-1]
    return filename
