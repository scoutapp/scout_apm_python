# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import httpretty
import pytest
import urllib3

from scout_apm.compat import urllib3_cert_pool_manager
from scout_apm.instruments.urllib3 import ensure_installed
from tests.compat import mock
from tests.tools import delete_attributes

mock_not_attempted = mock.patch(
    "scout_apm.instruments.urllib3.have_patched_pool_urlopen", new=False
)


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.urllib3",
            logging.DEBUG,
            "Instrumenting urllib3.",
        )
    ]


def test_install_fail_no_httpconnectionpool(caplog):
    mock_no_pool = mock.patch(
        "scout_apm.instruments.urllib3.HTTPConnectionPool", new=None
    )
    with mock_not_attempted, mock_no_pool:
        ensure_installed()

    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.urllib3",
            logging.DEBUG,
            "Instrumenting urllib3.",
        ),
        (
            "scout_apm.instruments.urllib3",
            logging.DEBUG,
            "Couldn't import urllib3.HTTPConnectionPool - probably not installed.",
        ),
    ]


def test_install_fail_no_urlopen_attribute(caplog):
    mock_pool = mock.patch("scout_apm.instruments.urllib3.HTTPConnectionPool")
    with mock_not_attempted, mock_pool as mocked_pool:
        # Remove urlopen attribute
        del mocked_pool.urlopen

        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.urllib3",
        logging.DEBUG,
        "Instrumenting urllib3.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.urllib3"
    assert level == logging.WARNING
    assert message.startswith(
        "Failed to instrument for Urllib3 HTTPConnectionPool.urlopen: AttributeError"
    )


def test_request(tracked_request):
    ensure_installed()
    with httpretty.enabled(allow_net_connect=False):
        httpretty.register_uri(
            httpretty.GET, "https://example.com/", body="Hello World!"
        )

        http = urllib3_cert_pool_manager()
        response = http.request("GET", "https://example.com")

    assert response.status == 200
    assert response.data == b"Hello World!"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "HTTP/GET"
    assert span.tags["url"] == "https://example.com:443/"


def test_second_request(tracked_request):
    ensure_installed()
    with tracked_request.span("Test"), httpretty.enabled(allow_net_connect=False):
        httpretty.register_uri(
            httpretty.GET, "https://example.com/foo", body="Hello World!"
        )
        httpretty.register_uri(
            httpretty.GET, "https://example.org/bar", body="Hello World!"
        )

        http = urllib3_cert_pool_manager()
        http.request("GET", "https://example.com/foo")
        http.request("GET", "https://example.org/bar")

    assert len(tracked_request.complete_spans) == 3
    assert (
        tracked_request.complete_spans[0].tags["url"] == "https://example.com:443/foo"
    )
    assert (
        tracked_request.complete_spans[1].tags["url"] == "https://example.org:443/bar"
    )


def test_request_type_error(tracked_request):
    ensure_installed()
    with pytest.raises(TypeError):
        http = urllib3_cert_pool_manager()
        connection = http.connection_from_host("example.com", scheme="https")
        connection.urlopen()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "HTTP/Unknown"
    assert span.tags["url"] == "Unknown"


def test_request_no_absolute_url(caplog, tracked_request):
    ensure_installed()
    delete_absolute_url = delete_attributes(urllib3.HTTPConnectionPool, "_absolute_url")
    with httpretty.enabled(allow_net_connect=False), delete_absolute_url:
        httpretty.register_uri(
            httpretty.GET, "https://example.com/", body="Hello World!"
        )

        http = urllib3_cert_pool_manager()
        response = http.request("GET", "https://example.com")

    assert response.status == 200
    assert response.data == b"Hello World!"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "HTTP/GET"
    assert span.tags["url"] == "Unknown"
