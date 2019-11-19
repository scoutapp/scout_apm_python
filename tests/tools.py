# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import functools
import sys
from contextlib import contextmanager

import pytest

from scout_apm.core import objtrace
from tests.compat import mock

skip_if_python_2 = pytest.mark.skipif(
    sys.version_info[0] == 2, reason="Requires Python 3"
)

skip_if_objtrace_not_extension = pytest.mark.skipif(
    not objtrace.is_extension, reason="Requires objtrace C extension"
)
skip_if_objtrace_is_extension = pytest.mark.skipif(
    objtrace.is_extension, reason="Requires no objtrace C extension"
)


@contextmanager
def delete_attributes(obj, *attributes):
    origs = [getattr(obj, attr) for attr in attributes]
    for attr in attributes:
        delattr(obj, attr)
    yield
    for attr, orig in zip(attributes, origs):
        setattr(obj, attr, orig)


@contextmanager
def pretend_package_unavailable(name):
    # Scrub it and sub-modules from sys.modules
    modules_without_package = sys.modules.copy()
    for module_name in list(modules_without_package):
        if module_name == name or module_name.startswith(name + "."):
            modules_without_package[module_name] = None
    mock_unimported = mock.patch.dict(sys.modules, modules_without_package, clear=True)

    # Make it impossible to re-import it
    mock_unfindable = mock.patch.object(sys, "path", [])

    with mock_unimported, mock_unfindable:
        yield


def async_test(func):
    """
    Wrap async_to_sync with another function because Pytest complains about
    collecting the resulting callable object as a test because it's not a true
    function:

    PytestCollectionWarning: cannot collect 'test_foo' because it is not a
    function.
    """
    # inner import because for Python 3.6+ tests only
    from asgiref.sync import async_to_sync

    sync_func = async_to_sync(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return sync_func(*args, **kwargs)

    return wrapper
