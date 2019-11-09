# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import httpretty
import pytest
import urllib3

from scout_apm.instruments.urllib3 import install
from tests.compat import mock


@pytest.fixture
def ensure_installed():
    # Should always successfully install in our test environment
    install()
    yield


mock_not_attempted = mock.patch("scout_apm.instruments.urllib3.attempted", new=False)


def test_install_fail_already_attempted(ensure_installed, caplog):
    result = install()

    assert result is False
    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.urllib3",
            logging.WARNING,
            "Urllib3 instrumentation has already been attempted to be installed.",
        )
    ]


def test_install_fail_no_httpconnectionpool(caplog):
    mock_no_pool = mock.patch(
        "scout_apm.instruments.urllib3.HTTPConnectionPool", new=None
    )
    with mock_not_attempted, mock_no_pool:
        result = install()

    assert result is False
    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.urllib3",
            logging.INFO,
            "Unable to import urllib3.HTTPConnectionPool",
        )
    ]


def test_install_fail_no_urlopen_attribute(caplog):
    mock_pool = mock.patch("scout_apm.instruments.urllib3.HTTPConnectionPool")
    with mock_not_attempted, mock_pool as mocked_pool:
        # Remove urlopen attribute
        del mocked_pool.urlopen

        result = install()

    assert result is False
    assert len(caplog.record_tuples) == 1
    logger, level, message = caplog.record_tuples[0]
    assert logger == "scout_apm.instruments.urllib3"
    assert level == logging.WARNING
    assert message.startswith(
        "Unable to instrument for Urllib3 HTTPConnectionPool.urlopen: AttributeError"
    )


def test_request(ensure_installed, tracked_request):
    with httpretty.enabled(allow_net_connect=False):
        httpretty.register_uri(
            httpretty.GET, "https://example.com/", body="Hello World!"
        )

        http = urllib3.PoolManager()
        response = http.request("GET", "https://example.com")

    assert response.status == 200
    assert response.data == b"Hello World!"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "HTTP/GET"
    assert span.tags["url"] == "https://example.com:443/"
