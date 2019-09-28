# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import platform
import subprocess


def is_valid_triple(triple):
    values = triple.split("-", 1)
    return (
        len(values) == 2
        and values[0] in ("i686", "x86_64", "unknown")
        and values[1]
        in ("unknown-linux-gnu", "unknown-linux-musl", "apple-darwin", "unknown")
    )


def get_triple():
    return "{arch}-{platform}".format(arch=get_arch(), platform=get_platform())


def get_arch():
    """
    What CPU are we on?
    """
    arch = platform.machine()
    if arch == "i686":
        return "i686"
    elif arch == "x86_64":
        return "x86_64"
    else:
        return "unknown"


def get_platform():
    """
    What Operating System (and sub-system like glibc / musl)
    """
    system_name = platform.system()
    if system_name == "Linux":
        libc = get_libc()
        return "unknown-linux-{libc}".format(libc=libc)
    elif system_name == "Darwin":
        return "apple-darwin"
    else:
        return "unknown"


_libc = None


def get_libc():
    """
    Alpine linux uses a non glibc version of the standard library, it uses
    the stripped down musl instead. The core agent can be built against it,
    but which one is running must be detected. Shelling out to `ldd`
    appears to be the most reliable way to do this.
    """
    global _libc
    if _libc is None:
        try:
            output = subprocess.check_output(
                ["ldd", "--version"], stderr=subprocess.STDOUT, close_fds=True
            )
        except (OSError, subprocess.CalledProcessError):
            _libc = "gnu"
        else:
            if b"musl" in output:
                _libc = "musl"
            else:
                _libc = "gnu"
    return _libc
