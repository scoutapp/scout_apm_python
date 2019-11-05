# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from contextlib import contextmanager

import elasticsearch
import elasticsearch.exceptions
import pytest

from scout_apm.instruments.elasticsearch import Instrument
from tests.compat import mock

# e.g. export ELASTICSEARCH_URL="http://localhost:9200/"
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL")
skip_if_elasticsearch_not_running = pytest.mark.skipif(
    ELASTICSEARCH_URL is None, reason="MongoDB isn't available"
)

instrument = Instrument()


@contextmanager
def es_with_scout():
    """
    Create an instrumented Elasticsearch connection.

    """
    es = elasticsearch.Elasticsearch(ELASTICSEARCH_URL)
    instrument.install()
    try:
        yield es
    finally:
        instrument.uninstall()


@skip_if_elasticsearch_not_running
def test_search(tracked_request):
    with es_with_scout() as es:
        es.search()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


@skip_if_elasticsearch_not_running
def test_search_arg_named_index(tracked_request):
    with es_with_scout() as es, pytest.raises(elasticsearch.exceptions.NotFoundError):
        es.search("myindex")

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Myindex/Search"


@skip_if_elasticsearch_not_running
def test_search_kwarg_named_index(tracked_request):
    with es_with_scout() as es, pytest.raises(elasticsearch.exceptions.NotFoundError):
        es.search(index="myindex")

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Myindex/Search"


@skip_if_elasticsearch_not_running
def test_search_arg_empty_index(tracked_request):
    with es_with_scout() as es:
        es.search("")

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


@skip_if_elasticsearch_not_running
def test_search_kwarg_empty_index(tracked_request):
    with es_with_scout() as es:
        es.search(index="")

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


@skip_if_elasticsearch_not_running
def test_search_kwarg_empty_index_list(tracked_request):
    with es_with_scout() as es:
        es.search(index=[])

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


@skip_if_elasticsearch_not_running
def test_perform_request_missing_url(tracked_request):
    with es_with_scout() as es:
        with pytest.raises(TypeError):
            # Transport instrumentation doesn't crash if url is missing.
            # This raises a TypeError when calling the original method.
            es.transport.perform_request("GET", params={}, body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


@skip_if_elasticsearch_not_running
def test_perform_request_bad_url(tracked_request):
    with es_with_scout() as es:
        with pytest.raises(TypeError):
            # Transport instrumentation doesn't crash if url has the wrong type.
            # This raises a TypeError when calling the original method.
            es.transport.perform_request("GET", None, params={}, body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


@skip_if_elasticsearch_not_running
def test_perform_request_unknown_url(tracked_request):
    with es_with_scout() as es:
        # Transport instrumentation doesn't crash if url is unknown.
        es.transport.perform_request("GET", "/_nodes", params={}, body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


@skip_if_elasticsearch_not_running
def test_perform_request_known_url(tracked_request):
    with es_with_scout() as es:
        # Transport instrumentation doesn't crash if url is unknown.
        es.transport.perform_request("GET", "/_count", params={}, body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Count"


def test_installed():
    with es_with_scout():
        assert Instrument.installed
    assert not Instrument.installed


def test_installable():
    with es_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_elasticsearch_module():
    with mock.patch("scout_apm.instruments.elasticsearch.Elasticsearch", new=None):
        assert not instrument.installable()


def test_install_no_elasticsearch_module():
    with mock.patch("scout_apm.instruments.elasticsearch.Elasticsearch", new=None):
        assert not instrument.install()
        assert not Instrument.installed


def test_instrument_client_install_missing_attribute():
    with mock.patch(
        "scout_apm.instruments.elasticsearch.Elasticsearch"
    ) as mock_elasticsearch:
        del mock_elasticsearch.bulk
    try:
        instrument.instrument_client()  # no crash
    finally:
        instrument.uninstrument_client()


@mock.patch(
    "scout_apm.instruments.elasticsearch.wrapt.decorator", side_effect=RuntimeError
)
def test_instrument_transport_install_failure(mock_decorator):
    assert not instrument.instrument_transport()


def test_install_is_idempotent():
    with es_with_scout():
        assert Instrument.installed
        instrument.install()  # does nothing, doesn't crash
        assert Instrument.installed


def test_uninstall_is_idempotent():
    assert not Instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
    assert not Instrument.installed
