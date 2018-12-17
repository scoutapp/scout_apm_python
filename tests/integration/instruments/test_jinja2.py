from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from contextlib import contextmanager

import jinja2

from scout_apm.instruments.jinja2 import Instrument

try:
    from unittest.mock import patch
except ImportError:  # Python 2
    from mock import patch


instrument = Instrument()


@contextmanager
def jinja2_with_scout():
    """
    Instrument Jinja2.

    """
    instrument.install()
    try:
        yield
    finally:
        instrument.uninstall()


@contextmanager
def no_jinja2():
    sys.modules["jinja2"] = None
    try:
        yield
    finally:
        sys.modules["jinja2"] = jinja2


def test_render():
    with jinja2_with_scout():
        template = jinja2.Template("Hello {{ name }}!")
        assert template.render(name="World") == "Hello World!"


def test_installed():
    assert not instrument.installed
    with jinja2_with_scout():
        assert instrument.installed
    assert not instrument.installed


def test_installable():
    assert instrument.installable()
    with jinja2_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_jinja2_module():
    with no_jinja2():
        assert not instrument.installable()


def test_install_no_jinja2_module():
    with no_jinja2():
        assert not instrument.install()
        assert not instrument.installed


@patch("scout_apm.instruments.jinja2.monkeypatch_method", side_effect=RuntimeError)
def test_install_failure(monkeypatch_method):
    try:
        assert not instrument.install()  # doesn't crash
    finally:
        # Currently installed = True even if installing failed.
        instrument.installed = False


def test_install_is_idempotent():
    with jinja2_with_scout():
        assert instrument.installed
        instrument.install()  # does nothing, doesn't crash


def test_uninstall_is_idempotent():
    assert not instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
