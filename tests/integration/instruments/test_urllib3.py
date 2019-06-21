# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
from contextlib import contextmanager

import pytest
import urllib3

from scout_apm.instruments.urllib3 import Instrument
from tests.compat import mock

# e.g. export URLLIB3_URL="http://httpbin.org/"
# or export URLLIB3_URL="http://localhost:9200/" (re-use Elasticsearch!)
URLLIB3_URL = os.environ.get("URLLIB3_URL")
if URLLIB3_URL is None:
    pytest.skip("HTTP test server isn't available", allow_module_level=True)


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


@contextmanager
def no_urllib3():
    sys.modules["urllib3"] = None
    try:
        yield
    finally:
        sys.modules["urllib3"] = urllib3


def test_request():
    with urllib3_with_scout():
        http = urllib3.PoolManager()
        response = http.request("GET", URLLIB3_URL)
        assert response.status == 200


# I can't trigger a failure to get instrument data through a public API.
# Somewhat surprisingly, the request still succeeds.
@mock.patch("urllib3.HTTPConnectionPool._absolute_url", side_effect=RuntimeError)
def test_urlopen_exception(_absolute_url):
    with urllib3_with_scout():
        http = urllib3.PoolManager()
        response = http.request("GET", URLLIB3_URL)
        assert response.status == 200


def test_installed():
    assert not Instrument.installed
    with urllib3_with_scout():
        assert Instrument.installed
    assert not Instrument.installed


def test_installable():
    assert instrument.installable()
    with urllib3_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_urllib3_module():
    with no_urllib3():
        assert not instrument.installable()


def test_install_no_urllib3_module():
    with no_urllib3():
        assert not instrument.install()
        assert not Instrument.installed


@mock.patch(
    "scout_apm.instruments.urllib3.monkeypatch_method", side_effect=RuntimeError
)
def test_install_failure(monkeypatch_method):
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
