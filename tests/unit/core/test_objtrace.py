# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

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


def test_enable_twice():
    objtrace.enable()
    objtrace.enable()


def test_disable_twice():
    objtrace.disable()
    objtrace.disable()


def test_get_counts():
    objtrace.enable()
    counts = objtrace.get_counts()
    assert isinstance(counts, tuple)
    assert len(counts) == 4
    assert all(isinstance(x, int) for x in counts)


@skip_if_objtrace_not_extension
def test_get_counts_allocations():
    lists = []
    objtrace.enable()
    lists.extend([1] for _ in range(100))
    objtrace.disable()
    counts = objtrace.get_counts()
    assert counts[0] > 0


@skip_if_objtrace_not_extension
@pytest.mark.skipif(
    sys.version_info < (3, 5), reason="Multiple allocations on Python 3.5+ only"
)
def test_get_counts_multiple_allocations():
    objtrace.enable()
    bytes(123)
    counts = objtrace.get_counts()
    assert counts[1] > 0


@skip_if_objtrace_not_extension
def test_get_counts_reallocations():
    items = []
    objtrace.enable()
    for i in range(1000):
        items.append(i)
    counts = objtrace.get_counts()
    assert counts[2] > 0


@skip_if_objtrace_not_extension
def test_get_counts_frees():
    objtrace.enable()
    for x in (1, 2, 3):
        y = x  # noqa: F841
    counts = objtrace.get_counts()
    assert counts[3] > 0
