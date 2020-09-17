# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.compat import string_type
from scout_apm.core import platform_detection
from tests.compat import mock


def test_get_triple():
    triple = platform_detection.get_triple()

    assert isinstance(triple, string_type)
    assert platform_detection.is_valid_triple(triple)


@pytest.mark.parametrize(
    "triple, validity",
    [
        ("x86_64-apple-darwin", True),
        ("i686-unknown-linux-gnu", True),
        ("unknown-unknown-linux-musl", True),
        ("", False),
        ("unknown", False),
        ("---", False),
    ],
)
def test_is_valid_triple(triple, validity):
    assert platform_detection.is_valid_triple(triple) == validity


@pytest.mark.parametrize(
    "machine, arch",
    [
        ("i686", "i686"),
        ("x86_64", "x86_64"),
        ("i386", "unknown"),
        ("arm", "unknown"),
        ("", "unknown"),
    ],
)
@mock.patch("platform.machine")
def test_get_arch(platform_machine, machine, arch):
    platform_machine.return_value = machine
    assert platform_detection.get_arch() == arch


@pytest.mark.parametrize(
    "system, platform",
    [
        ("Darwin", "apple-darwin"),
        ("Linux", "unknown-linux-musl"),
        ("Windows", "unknown"),
        ("", "unknown"),
    ],
)
@mock.patch("platform.system")
def test_get_platform(platform_system, system, platform):
    platform_system.return_value = system
    assert platform_detection.get_platform() == platform
