# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
import sysconfig

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


def test_capture_limit():
    def capture_recursive_bottom(limit):
        if limit <= 1:
            return backtrace.capture()
        else:
            return capture_recursive_bottom(limit - 1)

    stack = capture_recursive_bottom(backtrace.LIMIT * 2)
    assert len(stack) == backtrace.LIMIT


def test_capture_with_frame():
    def error():
        # Python 2 compatible way of getting the current frame.
        try:
            raise ZeroDivisionError
        except ZeroDivisionError:
            # Get the current frame
            return sys.exc_info()[2].tb_frame

    stack = backtrace.capture(error(), apply_filter=False)

    assert len(stack) >= 1
    for frame in stack:
        assert isinstance(frame, dict)
        assert set(frame.keys()) == {"file", "line", "function"}
        assert isinstance(frame["file"], str)
        assert isinstance(frame["line"], int)
        assert isinstance(frame["function"], str)

    assert stack[0]["file"] == format_py_filename(__file__)
    assert stack[0]["function"] == "error"
    assert stack[1]["function"] == "test_capture_with_frame"


def test_filter_frames():
    """Verify the frames from the library paths are excluded."""
    paths = sysconfig.get_paths()
    library_path = {paths["purelib"], paths["platlib"]}.pop()
    frames = [
        {"file": os.path.join(library_path, "test"), "line": 1, "function": "foo"},
        {"file": "/valid/path", "line": 1, "function": "foo"},
    ]

    actual = list(backtrace.filter_frames(frames))
    assert len(actual) == 1
    assert actual[0]["file"] == "/valid/path"
