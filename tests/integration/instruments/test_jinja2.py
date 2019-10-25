# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

import jinja2

from scout_apm.instruments.jinja2 import Instrument
from tests.compat import mock
from tests.tools import pretend_package_unavailable

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


def test_render():
    with jinja2_with_scout():
        template = jinja2.Template("Hello {{ name }}!")
        assert template.render(name="World") == "Hello World!"


def test_installed():
    assert not Instrument.installed
    with jinja2_with_scout():
        assert Instrument.installed
    assert not Instrument.installed


def test_installable():
    assert instrument.installable()
    with jinja2_with_scout():
        assert not instrument.installable()
    assert instrument.installable()


def test_installable_no_jinja2_module():
    with pretend_package_unavailable("jinja2"):
        assert not instrument.installable()


def test_install_no_jinja2_module():
    with pretend_package_unavailable("jinja2"):
        assert not instrument.install()
        assert not Instrument.installed


@mock.patch("scout_apm.instruments.jinja2.monkeypatch_method", side_effect=RuntimeError)
def test_install_failure(monkeypatch_method):
    try:
        assert not instrument.install()  # doesn't crash
    finally:
        # Currently installed = True even if installing failed.
        Instrument.installed = False


def test_install_is_idempotent():
    with jinja2_with_scout():
        assert Instrument.installed
        instrument.install()  # does nothing, doesn't crash
        assert Instrument.installed


def test_uninstall_is_idempotent():
    assert not Instrument.installed
    instrument.uninstall()  # does nothing, doesn't crash
    assert not Instrument.installed
