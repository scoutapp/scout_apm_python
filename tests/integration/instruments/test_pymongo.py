# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
from contextlib import contextmanager

import pymongo
import pytest

from scout_apm.instruments.pymongo import Instrument

try:
    from unittest.mock import patch
except ImportError:  # Python 2
    from mock import patch


# e.g. export MONGODB_URL="mongodb://localhost:27017/"
MONGODB_URL = os.environ.get("MONGODB_URL")
if MONGODB_URL is None:
    pytest.skip("MongoDB isn't available", allow_module_level=True)


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


@contextmanager
def no_pymongo():
    sys.modules["pymongo.collection"] = None
    try:
        yield
    finally:
        sys.modules["pymongo.collection"] = pymongo.collection


def test_find_one():
    with client_with_scout() as client:
        client.local.startup_log.find_one()


def test_installed():
    assert not instrument.installed
    with client_with_scout():
        assert instrument.installed
    assert not instrument.installed


def test_installable():
    assert instrument.installable()
    with client_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_pymongo_module():
    with no_pymongo():
        assert not instrument.installable()


def test_install_no_pymongo_module():
    with no_pymongo():
        assert not instrument.install()
        assert not instrument.installed


@patch("scout_apm.instruments.pymongo.monkeypatch_method", side_effect=RuntimeError)
def test_install_failure(monkeypatch_method):
    try:
        assert not instrument.install()  # doesn't crash
    finally:
        # Currently installed = True even if installing failed.
        instrument.installed = False


def test_install_is_idempotent():
    with client_with_scout():
        assert instrument.installed
        instrument.install()  # does nothing, doesn't crash


def test_uninstall_is_idempotent():
    assert not instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
