# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from contextlib import contextmanager

import pytest
import urllib3

from scout_apm.instruments.urllib3 import Instrument
from tests.compat import mock

# e.g. export URLLIB3_URL="http://httpbin.org/"
# or export URLLIB3_URL="http://localhost:9200/" (re-use Elasticsearch!)
URLLIB3_URL = os.environ.get("URLLIB3_URL")
skip_if_urllib3_url_unavailable = pytest.mark.skipif(
    URLLIB3_URL is None, reason="urllib3 URL isn't available"
)

instrument = Instrument()


@contextmanager
def urllib3_with_scout():
    """
    Create an instrumented urllib3 HTTP connection pool.

    """
    instrument.install()
    try:
        yield
    finally:
        instrument.uninstall()


@skip_if_urllib3_url_unavailable
def test_request():
    with urllib3_with_scout():
        http = urllib3.PoolManager()
        response = http.request("GET", URLLIB3_URL)
        assert response.status == 200


@skip_if_urllib3_url_unavailable
# I can't trigger a failure to get instrument data through a public API.
# Somewhat surprisingly, the request still succeeds.
@mock.patch("urllib3.HTTPConnectionPool._absolute_url", side_effect=RuntimeError)
def test_urlopen_exception(_absolute_url):
    with urllib3_with_scout():
        http = urllib3.PoolManager()
        response = http.request("GET", URLLIB3_URL)
        assert response.status == 200


def test_installed():
    with urllib3_with_scout():
        assert Instrument.installed
    assert not Instrument.installed


def test_installable():
    with urllib3_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_urllib3_module():
    with mock.patch("scout_apm.instruments.urllib3.HTTPConnectionPool", new=None):
        assert not instrument.installable()


def test_install_no_urllib3_module():
    with mock.patch("scout_apm.instruments.urllib3.HTTPConnectionPool", new=None):
        assert not instrument.install()
        assert not Instrument.installed


def test_install_failure_no_urlopen_attribute():
    with mock.patch(
        "scout_apm.instruments.urllib3.HTTPConnectionPool"
    ) as mock_http_connection_pool:
        del mock_http_connection_pool.urlopen
        try:
            assert not instrument.install()  # doesn't crash
        finally:
            # Currently installed = True even if installing failed.
            Instrument.installed = False


def test_install_is_idempotent():
    with urllib3_with_scout():
        assert Instrument.installed
        instrument.install()  # does nothing, doesn't crash
        assert Instrument.installed


def test_uninstall_is_idempotent():
    assert not Instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
    assert not Instrument.installed
