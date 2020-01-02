# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

import elasticsearch
import elasticsearch.exceptions
import pytest

from scout_apm.instruments.elasticsearch import CLIENT_METHODS, ensure_installed
from tests.compat import mock
from tests.tools import delete_attributes


@pytest.fixture(scope="module")
def elasticsearch_client():
    # e.g. export ELASTICSEARCH_URL="http://localhost:9200/"
    ensure_installed()
    if "ELASTICSEARCH_URL" not in os.environ:
        raise pytest.skip("Elasticsearch isn't available")
    yield elasticsearch.Elasticsearch(os.environ["ELASTICSEARCH_URL"])


def test_all_client_attributes_accounted_for():
    public_attributes = {
        m for m in dir(elasticsearch.Elasticsearch) if not m.startswith("_")
    }
    deliberately_ignored_attributes = set()
    assert (
        public_attributes - deliberately_ignored_attributes - set(CLIENT_METHODS)
    ) == set()


@pytest.mark.parametrize(["method_name"], [[x] for x in CLIENT_METHODS])
def test_all_client_methods_exist(method_name):
    assert hasattr(elasticsearch.Elasticsearch, method_name)


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.elasticsearch",
            logging.INFO,
            "Ensuring elasticsearch instrumentation is installed.",
        )
    ]


def test_ensure_installed_fail_no_client(caplog):
    mock_no_client = mock.patch(
        "scout_apm.instruments.elasticsearch.Elasticsearch", new=None
    )
    with mock_no_client:
        ensure_installed()

    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.elasticsearch",
            logging.INFO,
            "Ensuring elasticsearch instrumentation is installed.",
        ),
        (
            "scout_apm.instruments.elasticsearch",
            logging.INFO,
            "Unable to import elasticsearch.Elasticsearch",
        ),
    ]


def test_ensure_installed_fail_no_client_bulk(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.elasticsearch.have_patched_client", new=False
    )
    mock_no_bulk = delete_attributes(elasticsearch.Elasticsearch, "bulk")
    with mock_not_patched, mock_no_bulk:
        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.elasticsearch",
        logging.INFO,
        "Ensuring elasticsearch instrumentation is installed.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.elasticsearch"
    assert level == logging.WARNING
    assert message.startswith(
        "Unable to instrument elasticsearch.Elasticsearch.bulk: AttributeError"
    )


def test_ensure_installed_fail_no_transport_perform_request(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.elasticsearch.have_patched_transport", new=False
    )
    mock_transport = mock.patch("scout_apm.instruments.elasticsearch.Transport")
    with mock_not_patched, mock_transport as mocked_transport:
        del mocked_transport.perform_request

        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.elasticsearch",
        logging.INFO,
        "Ensuring elasticsearch instrumentation is installed.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.elasticsearch"
    assert level == logging.WARNING
    assert message.startswith(
        "Unable to instrument elasticsearch.Transport.perform_request: AttributeError"
    )


def test_ping(elasticsearch_client, tracked_request):
    elasticsearch_client.ping()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Ping"


def test_search(elasticsearch_client, tracked_request):
    elasticsearch_client.search()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


def test_search_arg_named_index(elasticsearch_client, tracked_request):
    with pytest.raises(elasticsearch.exceptions.NotFoundError):
        elasticsearch_client.search("myindex")

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Myindex/Search"


def test_search_kwarg_named_index(elasticsearch_client, tracked_request):
    with pytest.raises(elasticsearch.exceptions.NotFoundError):
        elasticsearch_client.search(index="myindex")

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Myindex/Search"


def test_search_arg_empty_index(elasticsearch_client, tracked_request):
    elasticsearch_client.search("")

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


def test_search_kwarg_empty_index(elasticsearch_client, tracked_request):
    elasticsearch_client.search(index="")

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


def test_search_kwarg_empty_index_list(elasticsearch_client, tracked_request):
    elasticsearch_client.search(index=[])

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


def test_search_kwarg_index_list(elasticsearch_client, tracked_request):
    with pytest.raises(elasticsearch.exceptions.NotFoundError):
        elasticsearch_client.search(index=["myindex", "myindex2"])

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Myindex,Myindex2/Search"


def test_perform_request_missing_url(elasticsearch_client, tracked_request):
    # Check Transport instrumentation doesn't crash if url is missing.
    # This raises a TypeError when calling the original method.
    with pytest.raises(TypeError):
        elasticsearch_client.transport.perform_request("GET", params={}, body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


def test_perform_request_bad_url(elasticsearch_client, tracked_request):
    with pytest.raises(TypeError):
        # Transport instrumentation doesn't crash if url has the wrong type.
        # This raises a TypeError when calling the original method.
        elasticsearch_client.transport.perform_request(
            "GET", None, params={}, body=None
        )

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


def test_perform_request_unknown_url(elasticsearch_client, tracked_request):
    # Transport instrumentation doesn't crash if url is unknown.
    elasticsearch_client.transport.perform_request(
        "GET", "/_nodes", params={}, body=None
    )

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


def test_perform_request_known_url(elasticsearch_client, tracked_request):
    # Transport instrumentation doesn't crash if url is unknown.
    elasticsearch_client.transport.perform_request(
        "GET", "/_count", params={}, body=None
    )

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Count"
