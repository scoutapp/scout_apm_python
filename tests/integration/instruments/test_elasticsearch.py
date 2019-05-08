# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
from contextlib import contextmanager

import elasticsearch
import pytest

from scout_apm.instruments.elasticsearch import Instrument

try:
    from unittest.mock import patch
except ImportError:  # Python 2
    from mock import patch


# e.g. export ELASTICSEARCH_URL="http://localhost:9200/"
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL")
if ELASTICSEARCH_URL is None:
    pytest.skip("Elasticsearch isn't available", allow_module_level=True)


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


@contextmanager
def no_elasticsearch():
    sys.modules["elasticsearch"] = None
    try:
        yield
    finally:
        sys.modules["elasticsearch"] = elasticsearch


def test_search():
    with es_with_scout() as es:
        es.search()


def test_search_no_indexes_string():
    with es_with_scout() as es:
        es.search(index="", body={"query": {"term": {"user": "kimchy"}}})


def test_search_no_indexes_list():
    with es_with_scout() as es:
        es.search(index=[], body={"query": {"term": {"user": "kimchy"}}})


def test_perform_request_missing_url():
    with es_with_scout() as es:
        with pytest.raises(TypeError):
            # Transport instrumentation doesn't crash if url is missing.
            # This raises a TypeError when calling the original method.
            es.transport.perform_request("GET", params={}, body=None)


def test_perform_request_bad_url():
    with es_with_scout() as es:
        with pytest.raises(TypeError):
            # Transport instrumentation doesn't crash if url has the wrong type.
            # This raises a TypeError when calling the original method.
            es.transport.perform_request("GET", None, params={}, body=None)


def test_perform_request_unknown_url():
    with es_with_scout() as es:
        # Transport instrumentation doesn't crash if url is unknown.
        es.transport.perform_request("GET", "/_nodes", params={}, body=None)


def test_installed():
    assert not instrument.installed
    with es_with_scout():
        assert instrument.installed
    assert not instrument.installed


def test_installable():
    assert instrument.installable()
    with es_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_elasticsearch_module():
    with no_elasticsearch():
        assert not instrument.installable()


def test_install_no_elasticsearch_module():
    with no_elasticsearch():
        assert not instrument.install()
        assert not instrument.installed


def test_instrument_client_no_elasticsearch_module():
    with no_elasticsearch():
        assert not instrument.instrument_client()


@patch(
    "scout_apm.instruments.elasticsearch.monkeypatch_method", side_effect=RuntimeError
)
def test_instrument_client_install_failure(monkeypatch_method):
    assert not instrument.instrument_client()


def test_instrument_transport_no_elasticsearch_module():
    with no_elasticsearch():
        assert not instrument.instrument_transport()


@patch(
    "scout_apm.instruments.elasticsearch.monkeypatch_method", side_effect=RuntimeError
)
def test_instrument_transport_install_failure(monkeypatch_method):
    assert not instrument.instrument_transport()


def test_install_is_idempotent():
    with es_with_scout():
        assert instrument.installed
        instrument.install()  # does nothing, doesn't crash


def test_uninstall_is_idempotent():
    assert not instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
