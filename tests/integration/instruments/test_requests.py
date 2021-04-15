# coding=utf-8
"""
Test requests package is instrumented via urllib3 instrumentation.

We don't instrument the package directly, but urllib3 underneath.
However, it's a good idea to verify it's working as expected.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import httpretty
import requests

from scout_apm.instruments.urllib3 import ensure_installed


def test_request(tracked_request):
    ensure_installed()
    with httpretty.enabled(allow_net_connect=False):
        httpretty.register_uri(
            httpretty.GET, "https://example.com/", body="Hello World!"
        )

        session = requests.Session()
        response = session.get("https://example.com")

    assert response.status_code == 200
    assert response.content == b"Hello World!"
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
        session = requests.Session()
        session.get("https://example.com/foo")
        session.get("https://example.org/bar")
    assert len(tracked_request.complete_spans) == 3
    assert (
        tracked_request.complete_spans[0].tags["url"] == "https://example.com:443/foo"
    )
    assert (
        tracked_request.complete_spans[1].tags["url"] == "https://example.org:443/bar"
    )
