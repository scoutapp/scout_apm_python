# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import platform


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
        # Previously we'd use either "-gnu" or "-musl" indicate which version
        # of libc we were built against. We now default to musl since it
        # reliably works on all platforms.
        return "unknown-linux-musl"
    elif system_name == "Darwin":
        return "apple-darwin"
    else:
        return "unknown"
