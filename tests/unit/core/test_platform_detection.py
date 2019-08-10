# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.compat import string_type
from scout_apm.core import platform_detection
from tests.compat import mock


def test_get_triple():
    assert isinstance(platform_detection.get_triple(), string_type)


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
        ("Linux", "unknown-linux-gnu"),
        ("Windows", "unknown"),
        ("", "unknown"),
    ],
)
@mock.patch("platform.system")
def test_get_platform(platform_system, system, platform):
    platform_system.return_value = system
    assert platform_detection.get_platform() == platform


@pytest.mark.parametrize(
    "output, libc",
    [
        (b"ldd (GNU libc) 2.17\n", "gnu"),
        (b"musl libc (x86_64)\nVersion 1.1.18\n", "musl"),
        (b"", "gnu"),
    ],
)
@mock.patch("subprocess.check_output")
def test_get_libc(check_output, output, libc):
    platform_detection._libc = None  # reset cache
    check_output.return_value = output
    assert platform_detection.get_libc() == libc


@mock.patch("subprocess.check_output")
def test_get_libc_no_ldd(check_output):
    platform_detection._libc = None  # reset cache
    check_output.side_effect = OSError
    assert platform_detection.get_libc() == "gnu"
