# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
import logging
import os

import elasticsearch
import elasticsearch.exceptions
import pytest

from scout_apm.instruments.elasticsearch import CLIENT_METHODS, ensure_installed
from tests.compat import mock
from tests.tools import delete_attributes, skip_if_python_2

skip_if_elasticsearch_v7 = pytest.mark.skipif(
    elasticsearch.VERSION < (8, 0, 0), reason="Requires ElasticSearch 8"
)


@pytest.fixture(scope="module")
def elasticsearch_client():
    # e.g. export ELASTICSEARCH_URL="http://localhost:9200/"
    ensure_installed()
    if "ELASTICSEARCH_URL" not in os.environ:
        raise pytest.skip("Elasticsearch isn't available")
    client = elasticsearch.Elasticsearch(os.environ["ELASTICSEARCH_URL"])
    try:
        yield client
    finally:
        client.close()


def test_all_client_attributes_accounted_for():
    public_attributes = {
        m for m in dir(elasticsearch.Elasticsearch) if not m.startswith("_")
    }
    deliberately_ignored_attributes = {"perform_request", "options", "transport"}
    wrapped_methods = {m.name for m in CLIENT_METHODS}

    assert (
        public_attributes - deliberately_ignored_attributes - wrapped_methods
    ) == set()


@pytest.mark.parametrize(["method_name"], [[m.name] for m in CLIENT_METHODS])
def test_all_client_methods_exist(method_name):
    assert hasattr(elasticsearch.Elasticsearch, method_name)


@skip_if_python_2
@pytest.mark.parametrize(
    ["method_name", "takes_index_argument"],
    [[m.name, m.takes_index_argument] for m in CLIENT_METHODS],
)
def test_all_client_methods_match_index_argument(method_name, takes_index_argument):
    signature = inspect.signature(getattr(elasticsearch.Elasticsearch, method_name))

    if takes_index_argument:
        assert "index" in signature.parameters
    else:
        assert "index" not in signature.parameters


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.elasticsearch",
            logging.DEBUG,
            "Instrumenting elasticsearch.",
        )
    ]


def test_ensure_installed_fail_no_client(caplog):
    mock_no_elasticsearch = mock.patch(
        "scout_apm.instruments.elasticsearch.Elasticsearch", new=None
    )
    mock_no_transport = mock.patch(
        "scout_apm.instruments.elasticsearch.Transport", new=None
    )
    with mock_no_elasticsearch, mock_no_transport:
        ensure_installed()

    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.elasticsearch",
            logging.DEBUG,
            "Instrumenting elasticsearch.",
        ),
        (
            "scout_apm.instruments.elasticsearch",
            logging.DEBUG,
            "Couldn't import elasticsearch.Elasticsearch - probably not installed.",
        ),
        (
            "scout_apm.instruments.elasticsearch",
            logging.DEBUG,
            "Couldn't import elasticsearch.Transport or elastic_transport.Transport "
            "- probably not installed.",
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
        logging.DEBUG,
        "Instrumenting elasticsearch.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.elasticsearch"
    assert level == logging.DEBUG
    assert message.startswith(
        "Failed to instrument elasticsearch.Elasticsearch.bulk: AttributeError"
    )


def test_ensure_installed_fail_no_client_methods(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.elasticsearch.have_patched_client", new=False
    )
    # Change the wrap methods to a boolean to cause an exception
    # and fail to wrap any of the client methods.
    mock_wrap_client_index_method = mock.patch(
        "scout_apm.instruments.elasticsearch.wrap_client_index_method", new=False
    )
    mock_wrap_client_method = mock.patch(
        "scout_apm.instruments.elasticsearch.wrap_client_method", new=False
    )
    with mock_not_patched, mock_wrap_client_index_method, mock_wrap_client_method:
        ensure_installed()

    logger, level, message = caplog.record_tuples[-1]
    assert logger == "scout_apm.instruments.elasticsearch"
    assert level == logging.WARNING
    assert message.startswith(
        "Failed to instrument any elasticsearch.Elasticsearch methods."
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
        logging.DEBUG,
        "Instrumenting elasticsearch.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.elasticsearch"
    assert level == logging.WARNING
    assert message.startswith(
        "Failed to instrument elasticsearch.Transport.perform_request: AttributeError"
    )


def test_ping(elasticsearch_client, tracked_request):
    elasticsearch_client.ping()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Ping"


def test_search_v7_api(elasticsearch_client, tracked_request):
    elasticsearch_client.search()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


@skip_if_elasticsearch_v7
def test_search(elasticsearch_client, tracked_request):
    elasticsearch_client.options().search()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown/Search"


@skip_if_python_2  # Cannot unwrap decorators on Python 2
def test_search_arg_named_index(elasticsearch_client, tracked_request):
    with pytest.raises(elasticsearch.exceptions.NotFoundError):
        # body, index
        elasticsearch_client.search(body=None, index="myindex")

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
    # body, index
    elasticsearch_client.search(body=None, index="")

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
    # This raises a TypeError and AttributeError when calling the original
    # method.
    with pytest.raises((TypeError, AttributeError)):
        elasticsearch_client.transport.perform_request("GET", body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


def test_perform_request_bad_url(elasticsearch_client, tracked_request):
    with pytest.raises((TypeError, AttributeError)):
        # Transport instrumentation doesn't crash if url has the wrong type.
        # This raises a TypeError when calling the original method.
        elasticsearch_client.transport.perform_request("GET", None, body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


def test_perform_request_unknown_url(elasticsearch_client, tracked_request):
    # Transport instrumentation doesn't crash if url is unknown.
    elasticsearch_client.transport.perform_request("GET", "/_nodes", body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Unknown"


def test_perform_request_known_url(elasticsearch_client, tracked_request):
    # Transport instrumentation doesn't crash if url is unknown.
    elasticsearch_client.transport.perform_request("GET", "/_count", body=None)

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Elasticsearch/Count"
