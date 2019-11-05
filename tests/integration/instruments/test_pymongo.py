# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from contextlib import contextmanager

import pymongo
import pytest

from scout_apm.instruments.pymongo import Instrument
from tests.compat import mock

# e.g. export MONGODB_URL="mongodb://localhost:27017/"
MONGODB_URL = os.environ.get("MONGODB_URL")
skip_if_mongodb_not_running = pytest.mark.skipif(
    MONGODB_URL is None, reason="MongoDB isn't available"
)

instrument = Instrument()


@contextmanager
def client_with_scout():
    """
    Create an instrumented MongoDB connection.
    """
    client = pymongo.MongoClient(MONGODB_URL)
    instrument.install()
    try:
        yield client
    finally:
        instrument.uninstall()


@skip_if_mongodb_not_running
def test_find_one():
    with client_with_scout() as client:
        client.local.startup_log.find_one()


@skip_if_mongodb_not_running
def test_installed():
    assert not Instrument.installed
    with client_with_scout():
        assert Instrument.installed
    assert not Instrument.installed


@skip_if_mongodb_not_running
def test_installable():
    assert instrument.installable()
    with client_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_pymongo_module():
    with mock.patch("scout_apm.instruments.pymongo.Collection", new=None):
        assert not instrument.installable()


def test_install_no_pymongo_module():
    with mock.patch("scout_apm.instruments.pymongo.Collection", new=None):
        assert not instrument.install()


def test_install_missing_attribute():
    with mock.patch("scout_apm.instruments.pymongo.Collection") as mock_collection:
        del mock_collection.aggregate
    try:
        instrument.install()  # no crash
    finally:
        instrument.uninstall()


def test_install_is_idempotent():
    with client_with_scout():
        assert Instrument.installed
        instrument.install()  # does nothing, doesn't crash
        assert Instrument.installed


def test_uninstall_is_idempotent():
    assert not Instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
    assert not Instrument.installed
