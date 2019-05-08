# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

try:
    from scout_apm.core import objtrace
except ImportError:
    objtrace = None

if objtrace is None:
    pytest.skip("objtrace extension isn't available", allow_module_level=True)


@pytest.fixture
def reset_objtrace_counts():
    if objtrace is None:
        return
    objtrace.reset_counts()
    try:
        yield
    finally:
        objtrace.reset_counts()


def test_enables_and_disabled(reset_objtrace_counts):
    objtrace.enable()
    objtrace.get_counts()
    objtrace.disable()


def test_allocation_counts(reset_objtrace_counts):
    lists = []
    objtrace.enable()
    for _ in range(100):
        lists.append([1])
    objtrace.disable()
    c = objtrace.get_counts()
    assert c[0] > 0


def test_frees_counts(reset_objtrace_counts):
    objtrace.enable()
    for x in (1, 2, 3):
        y = x  # noqa: F841
    c = objtrace.get_counts()
    assert c[3] > 0
