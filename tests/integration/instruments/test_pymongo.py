# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

import pymongo
import pytest

from scout_apm.instruments.pymongo import COLLECTION_METHODS, ensure_installed
from tests.compat import mock


@pytest.fixture(scope="module")
def pymongo_client():
    # e.g. export MONGODB_URL="mongodb://localhost:27017"
    ensure_installed()
    if "MONGODB_URL" not in os.environ:
        raise pytest.skip("MongoDB isn't available")
    yield pymongo.MongoClient(os.environ["MONGODB_URL"])


def test_all_collection_attributes_accounted_for():
    all_methods = {
        m for m in dir(pymongo.collection.Collection) if not m.startswith("_")
    }
    deliberately_ignored_methods = {
        # Properties:
        "codec_options",
        "database",
        "full_name",
        "name",
        "read_concern",
        "read_preference",
        "write_concern",
        # Non-querying methods:
        "initialize_ordered_bulk_op",
        "initialize_unordered_bulk_op",
        "next",
        "options",
        "with_options",
        # Returns a long running iterator rather than doing a direct query;
        # probably won't be used in web requests:
        "watch",
    }
    assert (
        all_methods - deliberately_ignored_methods - set(COLLECTION_METHODS)
    ) == set()


@pytest.mark.parametrize(["method_name"], [[x] for x in COLLECTION_METHODS])
def test_all_collection_methods_exist(method_name):
    assert hasattr(pymongo.collection.Collection, method_name)


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.pymongo",
            logging.DEBUG,
            "Instrumenting pymongo.",
        )
    ]


def test_ensure_installed_fail_no_collection(caplog):
    mock_no_collection = mock.patch(
        "scout_apm.instruments.pymongo.Collection", new=None
    )
    with mock_no_collection:
        ensure_installed()

    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.pymongo",
            logging.DEBUG,
            "Instrumenting pymongo.",
        ),
        (
            "scout_apm.instruments.pymongo",
            logging.DEBUG,
            "Couldn't import pymongo.Collection - probably not installed.",
        ),
    ]


def test_ensure_installed_fail_no_collection_aggregate(caplog):
    mock_not_patched = mock.patch(
        "scout_apm.instruments.pymongo.have_patched_collection", new=False
    )
    mock_collection = mock.patch("scout_apm.instruments.pymongo.Collection")
    with mock_not_patched, mock_collection as mocked_collection:
        del mocked_collection.aggregate

        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.pymongo",
        logging.DEBUG,
        "Instrumenting pymongo.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.pymongo"
    assert level == logging.WARNING
    assert message.startswith(
        "Failed to instrument pymongo.Collection.aggregate: AttributeError"
    )


def test_find_one(pymongo_client, tracked_request):
    pymongo_client.local.startup_log.find_one()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "MongoDB/startup_log.FindOne"
    assert span.tags["name"] == "startup_log"


def test_find_one_non_existent_database_and_collection(pymongo_client, tracked_request):
    pymongo_client["nonexistent"]["nonexistent"].find_one()

    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "MongoDB/nonexistent.FindOne"
    assert span.tags["name"] == "nonexistent"
