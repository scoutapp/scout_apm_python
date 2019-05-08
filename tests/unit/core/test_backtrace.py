# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core import backtrace


def test_traceback_contains_file_line_function():
    traceback = backtrace.capture()
    for frame in traceback:
        assert set(frame) == {"file", "line", "function"}


def test_traceback_returns_correct_types():
    traceback = backtrace.capture()
    for frame in traceback:
        assert isinstance(frame["file"], str)
        assert isinstance(frame["line"], int)
        assert isinstance(frame["function"], str)


def test_traceback_contains_inner_frame_first():
    traceback = backtrace.capture()
    # Consider removing the frame corresponding to the capture() call?
    # On Python 2, __file__ points to the compiled bytecode, not the source.
    assert traceback[0]["file"] == backtrace.__file__.replace(".pyc", ".py")
    assert traceback[1]["file"] == __file__.replace(".pyc", ".py")
