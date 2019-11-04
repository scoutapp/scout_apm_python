# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from contextlib import contextmanager

import pymongo
import pytest

from scout_apm.instruments.pymongo import Instrument
from tests.compat import mock
from tests.tools import pretend_package_unavailable

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
    with pretend_package_unavailable("pymongo"):
        assert not instrument.installable()


def test_install_no_pymongo_module():
    with pretend_package_unavailable("pymongo"):
        assert not instrument.install()


@mock.patch("scout_apm.instruments.pymongo.wrapt.decorator", side_effect=RuntimeError)
def test_install_failure(mock_decorator):
    try:
        assert not instrument.install()  # doesn't crash
    finally:
        # Currently installed = True even if installing failed.
        Instrument.installed = False


def test_install_is_idempotent():
    with client_with_scout():
        assert Instrument.installed
        instrument.install()  # does nothing, doesn't crash
        assert Instrument.installed


def test_uninstall_is_idempotent():
    assert not Instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
    assert not Instrument.installed
