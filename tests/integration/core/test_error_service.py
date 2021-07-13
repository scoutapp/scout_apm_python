# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
from datetime import datetime
from time import sleep

import httpretty
import pytest

from scout_apm.core.config import scout_config
from scout_apm.core.error_service import ErrorServiceThread
from tests.compat import gzip_decompress

WORKING_DIRECTORY = os.getcwd().encode("utf-8")


@pytest.fixture
def error_service_thread():
    service_thread = ErrorServiceThread.ensure_started()
    yield service_thread
    # ensure_stopped() already called by global stop_and_empty_core_agent_socket


@pytest.mark.parametrize(
    "config, decompressed_body, expected_headers, expected_uri",
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
            b'{"notifier": "scout_apm_python", "environment": "scout-test", '
            b'"root": "/tmp/", "problems": [{"foo": "bar"}]}',
            {"Agent-Hostname": "example.com", "X-Error-Count": "1"},
            "https://testserver/apps/error.scout?key=scout-app-key"
            "&name=scout+test+app",
        ),
        (
            {},
            b'{"notifier": "scout_apm_python", "environment": null, '
            b'"root": "' + WORKING_DIRECTORY + b'", "problems": [{"foo": "bar"}]}',
            {"Agent-Hostname": None, "X-Error-Count": "1"},
            "https://errors.scoutapm.com/apps/error.scout" "?name=Python+App",
        ),
    ],
)
def test_send(
    config, decompressed_body, expected_headers, expected_uri, error_service_thread
):
    scout_config.set(**config)

    def request_callback(request, uri, response_headers):
        assert uri == expected_uri
        for key, value in expected_headers.items():
            assert request.headers.get(key) == value
        assert gzip_decompress(request.body) == decompressed_body
        return [200, response_headers, "Hello world!"]

    try:
        with httpretty.enabled(allow_net_connect=False):
            httpretty.register_uri(
                httpretty.POST,
                "https://errors.scoutapm.com/apps/error.scout",
                body=request_callback,
            )
            ErrorServiceThread.send({"foo": "bar"})
            ErrorServiceThread.wait_until_drained()
    finally:
        scout_config.reset_all()


def test_send_batch(error_service_thread):
    def request_callback(request, uri, response_headers):
        decompressed_body = (
            b'{"notifier": "scout_apm_python", "environment": null, '
            b'"root": "'
            + WORKING_DIRECTORY
            + b'", "problems": [{"foo": 0}, {"foo": 1}, '
            b'{"foo": 2}, {"foo": 3}, {"foo": 4}]}'
        )
        assert gzip_decompress(request.body) == decompressed_body
        assert request.headers.get("X-Error-Count") == "5"
        return [200, response_headers, "Hello world!"]

    try:
        with httpretty.enabled(allow_net_connect=False):
            httpretty.register_uri(
                httpretty.POST,
                "https://errors.scoutapm.com/apps/error.scout",
                body=request_callback,
            )
            for i in range(5):
                ErrorServiceThread.send({"foo": i})
            ErrorServiceThread.wait_until_drained()
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
            ErrorServiceThread.send({"foo": "bar"})
            ErrorServiceThread.wait_until_drained()
    finally:
        scout_config.reset_all()
    assert caplog.record_tuples[-1][0] == "scout_apm.core.error_service"
    assert caplog.record_tuples[-1][1] == logging.DEBUG
    assert caplog.record_tuples[-1][2].startswith(
        "ErrorServiceThread exception on _send:"
    )


def test_send_unserializable_data(error_service_thread, caplog):
    with httpretty.enabled(allow_net_connect=False):
        ErrorServiceThread.send({"value": datetime.now()})
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
