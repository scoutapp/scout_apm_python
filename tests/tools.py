# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from contextlib import contextmanager

import pytest

from scout_apm.core import objtrace
from tests.compat import mock

skip_if_objtrace_not_extension = pytest.mark.skipif(
    not objtrace.is_extension, reason="Requires objtrace C extension"
)
skip_if_objtrace_is_extension = pytest.mark.skipif(
    not objtrace.is_extension, reason="Requires no objtrace C extension"
)


@contextmanager
def pretend_package_unavailable(name):
    # Scrub it and sub-modules from sys.modules
    modules_without_package = {
        k: v for k, v in sys.modules.items() if k != name or k.startswith(name + ".")
    }
    mock_unimported = mock.patch.dict(sys.modules, modules_without_package, clear=True)

    # Make it impossible to re-import it
    mock_unfindable = mock.patch.object(sys, "path", [])

    with mock_unimported, mock_unfindable:
        yield
