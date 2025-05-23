# coding=utf-8

import logging

import pytest
from mocket import Mocketizer
from mocket.mockhttp import Entry
from mocket.plugins.httpretty import httprettified, httpretty

from scout_apm.compat import urllib3_cert_pool_manager
from scout_apm.instruments.urllib3 import ensure_installed
from tests.compat import mock

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


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_request(tracked_request):
    ensure_installed()
    Entry.single_register(Entry.GET, "https://example.com/", body="Hello World!")

    with Mocketizer(strict_mode=True):
        http = urllib3_cert_pool_manager()
        response = http.request("GET", "https://example.com")

    assert response.status == 200
    assert response.data == b"Hello World!"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "HTTP/GET"
    assert span.tags["url"] == "https://example.com:443/"


def test_request_type_error(tracked_request):
    ensure_installed()
    with pytest.raises(TypeError):
        http = urllib3_cert_pool_manager()
        connection = http.connection_from_host("example.com", scheme="https")
        connection.urlopen()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "HTTP/Unknown"
    assert span.tags["url"] == "https://example.com:443/"


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
@httprettified
def test_request_ignore_errors_host(tracked_request):
    ensure_installed()
    httpretty.register_uri(
        httpretty.POST, "https://errors.scoutapm.com", body="Hello World!"
    )

    http = urllib3_cert_pool_manager()
    response = http.request("POST", "https://errors.scoutapm.com")

    assert response.status == 200
    assert response.data == b"Hello World!"
    assert len(tracked_request.complete_spans) == 0
