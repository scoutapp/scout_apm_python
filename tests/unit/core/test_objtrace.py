# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.core import objtrace
from tests.tools import skip_if_objtrace_not_extension


@pytest.fixture(autouse=True)
def reset_objtrace_counts():
    objtrace.reset_counts()
    try:
        yield
    finally:
        objtrace.reset_counts()


def test_enables_and_disabled():
    objtrace.enable()
    objtrace.get_counts()
    objtrace.disable()


@skip_if_objtrace_not_extension
def test_allocation_counts():
    lists = []
    objtrace.enable()
    for _ in range(100):
        lists.append([1])
    objtrace.disable()
    c = objtrace.get_counts()
    assert c[0] > 0


@skip_if_objtrace_not_extension
def test_frees_counts():
    objtrace.enable()
    for x in (1, 2, 3):
        y = x  # noqa: F841
    c = objtrace.get_counts()
    assert c[3] > 0
