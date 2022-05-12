# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
import sysconfig

import pytest

from scout_apm.core import backtrace


def get_tb():
    # Python 2 compatible way of getting the current frame.
    try:
        raise ZeroDivisionError
    except ZeroDivisionError:
        # Get the current frame
        return sys.exc_info()[2]


def test_capture_backtrace():
    stack = backtrace.capture_backtrace()

    assert isinstance(stack, list)
    assert len(stack) >= 1
    for frame in stack:
        assert isinstance(frame, dict)
        assert set(frame.keys()) == {"file", "full_path", "line", "function"}
        assert isinstance(frame["file"], str)
        assert isinstance(frame["full_path"], str)
        assert isinstance(frame["line"], int)
        assert isinstance(frame["function"], str)

    assert stack[0]["file"] == "scout_apm/core/backtrace.py"
    assert stack[0]["full_path"].endswith("/scout_apm/core/backtrace.py")
    assert stack[0]["function"] == "filter_frames"
    assert stack[1]["file"] == "scout_apm/core/backtrace.py"
    assert stack[1]["full_path"].endswith("/scout_apm/core/backtrace.py")
    assert stack[1]["function"] == "capture_backtrace"
    assert stack[2]["file"] == "tests/unit/core/test_backtrace.py"
    assert stack[2]["full_path"].endswith("/tests/unit/core/test_backtrace.py")
    assert stack[2]["function"] == "test_capture_backtrace"


def test_capture_backtrace_limit():
    def capture_recursive_bottom(limit):
        if limit <= 1:
            return backtrace.capture_backtrace()
        else:
            return capture_recursive_bottom(limit - 1)

    stack = capture_recursive_bottom(backtrace.LIMIT * 2)
    assert len(stack) == backtrace.LIMIT


def test_filter_frames():
    """Verify the frames from the library paths are excluded."""
    paths = sysconfig.get_paths()
    library_path = {paths["purelib"], paths["platlib"]}.pop()
    frames = [
        {"file": os.path.join(library_path, "test"), "line": 1, "function": "foo"},
        {"file": "tests/unit/core/test_backtrace.py", "line": 1, "function": "foo"},
    ]

    actual = list(backtrace.filter_frames(frames))
    assert len(actual) == 1
    assert actual[0]["file"] == "tests/unit/core/test_backtrace.py"


def test_capture_stacktrace():
    stack = backtrace.capture_stacktrace(get_tb())

    assert len(stack) == 1
    for frame in stack:
        assert isinstance(frame, dict)
        assert set(frame.keys()) == {"file", "full_path", "line", "function"}
        assert isinstance(frame["file"], str)
        assert isinstance(frame["full_path"], str)
        assert isinstance(frame["line"], int)
        assert isinstance(frame["function"], str)

    assert stack[0]["file"] == "tests/unit/core/test_backtrace.py"
    assert stack[0]["full_path"].endswith("/tests/unit/core/test_backtrace.py")
    assert stack[0]["function"] == "get_tb"


def test_module_filepath():
    frame = get_tb().tb_frame
    module = frame.f_globals["__name__"]
    filepath = frame.f_code.co_filename
    assert (
        backtrace.module_filepath(module, filepath)
        == "tests/unit/core/test_backtrace.py"
    )


@pytest.fixture
def test_package_as_namespace_package():
    original = sys.modules["tests"].__file__
    sys.modules["tests"].__file__ = None
    yield
    sys.modules["tests"].__file__ = original


def test_module_filepath_with_namespace(test_package_as_namespace_package):
    frame = get_tb().tb_frame
    module = frame.f_globals["__name__"]
    filepath = frame.f_code.co_filename
    assert (
        backtrace.module_filepath(module, filepath)
        == "tests/unit/core/test_backtrace.py"
    )


@pytest.fixture(
    params=[
        # Invalid path case
        [None, "invalid"],
        # Raise an error case
        [None, [None]],
        # No file or path case.
        [None, None],
    ]
)
def error_module(request):
    orig_file = sys.modules["tests"].__file__
    orig_path = sys.modules["tests"].__path__
    sys.modules["tests"].__file__ = request.param[0]
    sys.modules["tests"].__path__ = request.param[1]
    yield
    sys.modules["tests"].__file__ = orig_file
    sys.modules["tests"].__path__ = orig_path


def test_module_filepath_error_flows(error_module):
    frame = get_tb().tb_frame
    module = frame.f_globals["__name__"]
    filepath = frame.f_code.co_filename
    full_path = backtrace.module_filepath(module, filepath)
    assert full_path != "/tests/unit/core/test_backtrace.py"
    assert full_path.endswith("/tests/unit/core/test_backtrace.py")


def test_filepaths_no_module():
    """When there is no module a tuple should still be returned"""
    frame = get_tb().tb_frame
    frame.f_globals["__name__"] = None
    actual = backtrace.filepaths(frame)
    assert len(actual) == 2
    assert actual[0].endswith("tests/unit/core/test_backtrace.py")
    assert actual[0].endswith("tests/unit/core/test_backtrace.py")
