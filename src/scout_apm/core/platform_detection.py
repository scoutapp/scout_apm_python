from __future__ import absolute_import, division, print_function, unicode_literals

import platform
import subprocess


class PlatformDetection(object):
    """
    This helps figuring out what platform we're running on, so we can download
    the correct binary build of Core Agent.
    """

    @classmethod
    def get_triple(cls):
        return "{arch}-{platform}".format(arch=cls.arch(), platform=cls.platform())

    @classmethod
    def arch(cls):
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

    @classmethod
    def platform(cls):
        """
        What Operating System (and sub-system like glibc / musl)
        """
        system_name = platform.system()
        if system_name == "Linux":
            libc = cls.libc()
            return "unknown-linux-{libc}".format(libc=libc)
        elif system_name == "Darwin":
            return "apple-darwin"
        else:
            return "unknown"

    @classmethod
    def libc(cls):
        """
        Alpine linux uses a non glibc version of the standard library, it uses
        the stripped down musl instead. The core agent can be built against it,
        but which one is running must be detected. Shelling out to `ldd`
        appears to be the most reliable way to do this.
        """
        try:
            output = subprocess.check_output(
                ["ldd", "--version"], stderr=subprocess.STDOUT
            )
        except (OSError, subprocess.CalledProcessError):
            return "gnu"
        else:
            if b"musl" in output:
                return "musl"
            else:
                return "gnu"
