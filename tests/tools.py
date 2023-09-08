# coding=utf-8

import sys
from contextlib import contextmanager

try:
    from contextvars import ContextVar
except ImportError:
    ContextVar = None

import pytest

from scout_apm.core import objtrace
from scout_apm.core.n_plus_one_tracker import NPlusOneTracker
from tests.compat import mock, nullcontext

skip_if_objtrace_not_extension = pytest.mark.skipif(
    not objtrace.is_extension, reason="Requires objtrace C extension"
)
skip_if_objtrace_is_extension = pytest.mark.skipif(
    objtrace.is_extension, reason="Requires no objtrace C extension"
)

skip_if_missing_context_vars = pytest.mark.skipif(
    ContextVar is None, reason="Requires ContextVars"
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


@contextmanager
def n_plus_one_thresholds(count=None, duration=None):
    """
    Reduce the thresholds on NPlusOneTracker to force capture without having to
    run a lot of slow queries
    """
    if count is None:
        mock_count = nullcontext
    else:
        mock_count = mock.patch.object(NPlusOneTracker, "COUNT_THRESHOLD", new=count)
    if duration is None:
        mock_duration = nullcontext
    else:
        mock_duration = mock.patch.object(
            NPlusOneTracker, "DURATION_THRESHOLD", new=duration
        )
    with mock_count, mock_duration:
        yield


def asgi_http_scope(headers=None, **kwargs):
    if headers is None:
        headers = {}
    headers = [
        [k.lower().encode("latin-1"), v.encode("latin-1")] for k, v in headers.items()
    ]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": "GET",
        "query_string": b"",
        "server": ("testserver", 80),
        "headers": headers,
    }
    scope.update(kwargs)
    return scope
