from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core.config import ScoutConfig
from scout_apm.core.ignore import ignore_path


def test_ignore():
    ScoutConfig.set(ignore=["/health"])

    assert ignore_path("/health")
    assert ignore_path("/health/foo")
    assert not ignore_path("/users")

    ScoutConfig.reset_all()


def test_ignore_multiple_prefixes():
    ScoutConfig.set(ignore=["/health", "/api"])

    assert ignore_path("/health")
    assert ignore_path("/health/foo")
    assert ignore_path("/api")
    assert ignore_path("/api/foo")
    assert not ignore_path("/users")

    ScoutConfig.reset_all()
