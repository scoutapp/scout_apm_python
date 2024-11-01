# coding=utf-8

import json
import logging
import os
from datetime import datetime, timezone
from time import sleep

import httpretty
import pytest

from scout_apm.core.config import scout_config
from scout_apm.core.error_service import ErrorServiceThread
from tests.compat import gzip_decompress

WORKING_DIRECTORY = os.getcwd()


@pytest.fixture
def error_service_thread():
    service_thread = ErrorServiceThread.ensure_started()
    yield service_thread
    # ensure_stopped() already called by global stop_and_empty_core_agent_socket


@pytest.fixture(params=[True])
def error_monitor_errors(error_monitor_errors):
    """
    Override error_monitor_errors to capture the messages sent to
    ErrorServiceThread
    """
    return error_monitor_errors


@pytest.mark.parametrize(
    "config, decoded_body, expected_headers, expected_uri",
    [
        (
            {
                "key": "scout-app-key",
                "app": "scout test app",
                "hostname": "example.com",
                "environment": "scout-test",
                "application_root": "/tmp/",
                "errors_host": "https://testserver",
            },
            {
                "notifier": "scout_apm_python",
                "environment": "scout-test",
                "root": "/tmp/",
                "problems": [{"foo": "BØØM!"}],
            },
            {"Agent-Hostname": "example.com", "X-Error-Count": "1"},
            "https://testserver/apps/error.scout?key=scout-app-key"
            "&name=scout+test+app",
        ),
        (
            {},
            {
                "notifier": "scout_apm_python",
                "environment": None,
                "root": WORKING_DIRECTORY,
                "problems": [{"foo": "BØØM!"}],
            },
            {"Agent-Hostname": None, "X-Error-Count": "1"},
            "https://errors.scoutapm.com/apps/error.scout?name=Python+App",
        ),
    ],
)
def test_send(
    config, decoded_body, expected_headers, expected_uri, error_service_thread
):
    scout_config.set(**config)

    try:
        with httpretty.enabled(allow_net_connect=False):
            httpretty.register_uri(
                httpretty.POST,
                expected_uri,
                body="Hello World!",
            )
            ErrorServiceThread.send(error={"foo": "BØØM!"})
            ErrorServiceThread.wait_until_drained()

            request = httpretty.last_request()
            assert (
                json.loads(gzip_decompress(request.body).decode("utf-8"))
                == decoded_body
            )
            assert request.headers.get("X-Error-Count") == "1"
    finally:
        scout_config.reset_all()


def test_send_batch(error_service_thread):
    decompressed_body = {
        "notifier": "scout_apm_python",
        "root": WORKING_DIRECTORY,
        "environment": None,
        "problems": [{"foo": 0}, {"foo": 1}, {"foo": 2}, {"foo": 3}, {"foo": 4}],
    }
    try:
        with httpretty.enabled(allow_net_connect=False):
            httpretty.register_uri(
                httpretty.POST,
                "https://errors.scoutapm.com/apps/error.scout",
                body="Hello world!",
            )
            for i in range(5):
                ErrorServiceThread.send(error={"foo": i})
            ErrorServiceThread.wait_until_drained()

            request = httpretty.last_request()
            assert (
                json.loads(gzip_decompress(request.body).decode("utf-8"))
                == decompressed_body
            )
            assert request.headers.get("X-Error-Count") == "5"
    finally:
        scout_config.reset_all()


def test_send_api_error(error_service_thread, caplog):
    try:
        with httpretty.enabled(allow_net_connect=False):
            httpretty.register_uri(
                httpretty.POST,
                "https://errors.scoutapm.com/apps/error.scout",
                body="Unexpected Error",
                status=500,
            )
            ErrorServiceThread.send(error={"foo": "BØØM!"})
            ErrorServiceThread.wait_until_drained()
    finally:
        scout_config.reset_all()
    assert caplog.record_tuples[-1][0] == "scout_apm.core.error_service"
    assert caplog.record_tuples[-1][1] == logging.DEBUG
    assert caplog.record_tuples[-1][2].startswith(
        "ErrorServiceThread 500 response error on _send:"
    )


def test_send_unserializable_data(error_service_thread, caplog):
    with httpretty.enabled(allow_net_connect=False):
        ErrorServiceThread.send(error={"value": datetime.now(tz=timezone.utc)})
        ErrorServiceThread.wait_until_drained()

    if ErrorServiceThread._queue.empty() and not caplog.record_tuples:
        # py38-django20 and py36-django11 tend to fail
        # here by indicating the log never occurred despite
        # the message being pushed down.
        sleep(2)
    assert caplog.record_tuples[-1][0] == "scout_apm.core.error_service"
    assert caplog.record_tuples[-1][1] == logging.DEBUG
    assert caplog.record_tuples[-1][2].startswith(
        "Exception when serializing error message:"
    )
