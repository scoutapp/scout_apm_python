# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import time

import pytest

from scout_apm.core.util import CUTOFF_EPOCH_S, convert_ambiguous_timestamp_to_ns, octal

ref_time_s = time.mktime((2019, 6, 1, 0, 0, 0, 0, 0, 0))


@pytest.mark.parametrize(
    "given,expected",
    [
        (ref_time_s, ref_time_s * 1e9),
        (ref_time_s * 1e3, ref_time_s * 1e9),
        (ref_time_s * 1e6, ref_time_s * 1e9),
        (CUTOFF_EPOCH_S + 10, (CUTOFF_EPOCH_S + 10) * 1e9),
        (0.0, 0.0),
        (1000.0, 0.0),
        (float("inf"), float("inf")),
        (float("-inf"), 0.0),
        (float("nan"), 0.0),
    ],
)
def test_convert_ambiguous_timestamp_to_ns(given, expected):
    assert convert_ambiguous_timestamp_to_ns(given) == expected


def test_octal_with_valid_integer():
    assert 0o700 == octal(700)


def test_octal_with_valid_string():
    assert 0o700 == octal("700")


def test_octal_raises_valueerror_on_invalid_value():
    try:
        octal("THIS IS INVALID")
    except ValueError:
        pass
