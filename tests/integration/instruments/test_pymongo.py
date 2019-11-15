# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

import pymongo
import pytest

from scout_apm.instruments.pymongo import ensure_installed
from tests.compat import mock


@pytest.fixture(scope="module")
def pymongo_client():
    # e.g. export MONGODB_URL="mongodb://localhost:27017"
    ensure_installed()
    if "MONGODB_URL" not in os.environ:
        raise pytest.skip("MongoDB isn't available")
    yield pymongo.MongoClient(os.environ["MONGODB_URL"])


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.pymongo",
            logging.INFO,
            "Ensuring pymongo instrumentation is installed.",
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
            logging.INFO,
            "Ensuring pymongo instrumentation is installed.",
        ),
        (
            "scout_apm.instruments.pymongo",
            logging.INFO,
            "Unable to import pymongo.Collection",
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
        logging.INFO,
        "Ensuring pymongo instrumentation is installed.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.pymongo"
    assert level == logging.WARNING
    assert message.startswith(
        "Unable to instrument pymongo.Collection.aggregate: AttributeError"
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
