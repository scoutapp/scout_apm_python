# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import itertools
import os
import sys
import sysconfig
import traceback
import warnings
from logging import getLogger

logger = getLogger(__name__)

# Maximum non-Scout frames to target retrieving
LIMIT = 50
# How many upper frames from inside Scout to ignore
IGNORED = 1


def filter_frames(frames):
    """Filter the stack trace frames down to non-library code."""
    paths = sysconfig.get_paths()
    library_paths = {paths["purelib"], paths["platlib"]}
    for frame in frames:
        if not any(frame["file"].startswith(exclusion) for exclusion in library_paths):
            yield frame


def module_filepath(module, filepath):
    """Get the filepath relative to the base module."""
    root_module_name = module.split(".", 1)[0]
    if root_module_name == module:
        return os.path.basename(filepath)

    module_dir = None
    root_module = sys.modules[root_module_name]
    try:
        if root_module.__file__:
            module_dir = root_module.__file__.rsplit(os.sep, 2)[0]
        elif root_module.__path__ and isinstance(root_module.__path__, (list, tuple)):
            # Default to using the first path specified for the module.
            module_dir = root_module.__path__[0].rsplit(os.sep, 1)[0]
            if len(root_module.__path__) > 1:
                logger.debug(
                    "{} has {} paths. Use the first and ignore the rest.".format(
                        root_module, len(root_module.__path__)
                    )
                )
    except Exception as exc:
        logger.debug(
            "Error processing module {} and filepath {}".format(root_module, filepath),
            exc_info=exc,
        )

    return filepath.split(module_dir, 1)[-1].lstrip(os.sep) if module_dir else filepath


def filepaths(frame):
    """Get the filepath for frame."""
    module = frame.f_globals.get("__name__", None)
    filepath = frame.f_code.co_filename

    if filepath.endswith(".pyc"):
        filepath = filepath[:-1]

    return filepath, (module_filepath(module, filepath) if module else filepath)


if sys.version_info >= (3, 5):

    def stacktrace_walker(tb):
        """Iterate over each frame of the stack downards for exceptions."""
        for frame, lineno in traceback.walk_tb(tb):
            name = frame.f_code.co_name
            full_path, relative_path = filepaths(frame)
            yield {
                "file": relative_path,
                "full_path": full_path,
                "line": lineno,
                "function": name,
            }

    def backtrace_walker():
        """Iterate over each frame of the stack upwards.

        Taken from python3/traceback.ExtractSummary.extract to support
        iterating over the entire stack, but without creating a large
        data structure.
        """
        start_frame = sys._getframe().f_back
        for frame, lineno in traceback.walk_stack(start_frame):
            name = frame.f_code.co_name
            full_path, relative_path = filepaths(frame)
            yield {
                "file": relative_path,
                "full_path": full_path,
                "line": lineno,
                "function": name,
            }

else:

    def stacktrace_walker(tb):
        """Iterate over each frame of the stack downards for exceptions."""
        while tb is not None:
            lineno = tb.tb_lineno
            name = tb.tb_frame.f_code.co_name
            full_path, relative_path = filepaths(tb.tb_frame)
            yield {
                "file": relative_path,
                "full_path": full_path,
                "line": lineno,
                "function": name,
            }
            tb = tb.tb_next

    def backtrace_walker():
        """Iterate over each frame of the stack upwards.

        Taken from python2.7/traceback.extract_stack to support iterating
        over the entire stack, but without creating a large data structure.
        """
        try:
            raise ZeroDivisionError
        except ZeroDivisionError:
            # Get the current frame
            frame = sys.exc_info()[2].tb_frame.f_back

        while frame is not None:
            lineno = frame.f_lineno
            name = frame.f_code.co_name
            full_path, relative_path = filepaths(frame)
            yield {
                "file": relative_path,
                "full_path": full_path,
                "line": lineno,
                "function": name,
            }
            frame = frame.f_back


def capture_backtrace():
    walker = filter_frames(backtrace_walker())
    return list(itertools.islice(walker, LIMIT))


def capture_stacktrace(tb):
    walker = stacktrace_walker(tb)
    return list(reversed(list(itertools.islice(walker, LIMIT))))


def capture():
    warnings.warn(
        "capture is deprecated, instead use capture_backtrace instead.",
        DeprecationWarning,
        2,
    )
    return capture_backtrace()
