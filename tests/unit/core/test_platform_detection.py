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
    "machine, system, result",
    [
        ("x86_64", "Darwin", "x86_64-apple-darwin"),
        ("aarch64", "Darwin", "x86_64-apple-darwin"),
        ("x86_64", "Linux", "x86_64-unknown-linux-musl"),
        ("aarch64", "Linux", "aarch64-unknown-linux-musl"),
    ],
)
@mock.patch("platform.machine")
@mock.patch("platform.system")
def test_aarch64_apple_darwin_override(
    platform_system, platform_machine, machine, system, result
):
    platform_machine.return_value = machine
    platform_system.return_value = system
    assert platform_detection.get_triple() == result


@pytest.mark.parametrize(
    "triple, validity",
    [
        ("x86_64-apple-darwin", True),
        ("i686-unknown-linux-gnu", True),
        ("aarch64-unknown-linux-gnu", True),
        ("aarch64-unknown-linux-musl", True),
        ("x86_64-apple-darwin", True),
        ("unknown-unknown-linux-musl", True),
        ("", False),
        ("unknown", False),
        ("---", False),
        ("i686-apple-darwin", True),
        ("aarch64-apple-darwin", False),
    ],
)
def test_is_valid_triple(triple, validity):
    assert platform_detection.is_valid_triple(triple) == validity


@pytest.mark.parametrize(
    "machine, arch",
    [
        ("i686", "i686"),
        ("x86_64", "x86_64"),
        ("aarch64", "aarch64"),
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
