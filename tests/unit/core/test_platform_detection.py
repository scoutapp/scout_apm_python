# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import pytest

from scout_apm.core.platform_detection import PlatformDetection

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch


string_type = str if sys.version_info[0] >= 3 else basestring  # noqa: F821


def test_get_triple():
    assert isinstance(PlatformDetection.get_triple(), string_type)


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
@patch("platform.machine")
def test_arch(platform_machine, machine, arch):
    platform_machine.return_value = machine
    assert PlatformDetection.arch() == arch


@pytest.mark.parametrize(
    "system, platform",
    [
        ("Darwin", "apple-darwin"),
        ("Linux", "unknown-linux-gnu"),
        ("Windows", "unknown"),
        ("", "unknown"),
    ],
)
@patch("platform.system")
def test_platform(platform_system, system, platform):
    platform_system.return_value = system
    assert PlatformDetection.platform() == platform


@pytest.mark.parametrize(
    "output, libc",
    [
        (b"ldd (GNU libc) 2.17\n", "gnu"),
        (b"musl libc (x86_64)\nVersion 1.1.18\n", "musl"),
        (b"", "gnu"),
    ],
)
@patch("subprocess.check_output")
def test_libc(check_output, output, libc):
    check_output.return_value = output
    assert PlatformDetection.libc() == libc


@patch("subprocess.check_output")
def test_libc_no_ldd(check_output):
    check_output.side_effect = OSError
    assert PlatformDetection.libc() == "gnu"
