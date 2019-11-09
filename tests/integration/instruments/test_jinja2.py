# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import jinja2
import pytest

from scout_apm.instruments.jinja2 import install
from tests.compat import mock


@pytest.fixture
def ensure_installed():
    # Should always successfully install in our test environment
    install()
    yield


mock_not_attempted = mock.patch("scout_apm.instruments.jinja2.attempted", new=False)


def test_install_fail_already_attempted(ensure_installed, caplog):
    result = install()

    assert result is False
    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.jinja2",
            logging.WARNING,
            "Jinja2 instrumentation has already been attempted to be installed.",
        )
    ]


def test_install_fail_no_jinja2_template(caplog):
    with mock_not_attempted, mock.patch(
        "scout_apm.instruments.jinja2.Template", new=None
    ):
        result = install()

    assert result is False
    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.jinja2",
            logging.INFO,
            "Unable to import Jinja2's Template",
        )
    ]


def test_install_fail_no_render_attribute(caplog):
    mock_template = mock.patch("scout_apm.instruments.jinja2.Template")
    with mock_not_attempted, mock_template as mocked_template:
        # Remove render attrbiute
        del mocked_template.render

        result = install()

    assert result is False
    assert len(caplog.record_tuples) == 1
    logger, level, message = caplog.record_tuples[0]
    assert logger == "scout_apm.instruments.jinja2"
    assert level == logging.WARNING
    assert message.startswith(
        "Unable to instrument for Jinja2 Template.render: AttributeError"
    )


def test_render(ensure_installed, tracked_request):
    template = jinja2.Template("Hello {{ name }}!")

    result = template.render(name="World")

    assert result == "Hello World!"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Template/Render"
    assert span.tags["name"] is None


def test_render_template_name(ensure_installed, tracked_request):
    template = jinja2.Template("Hello {{ name }}!")
    template.name = "mytemplate.html"

    result = template.render(name="World")

    assert result == "Hello World!"
    assert tracked_request.complete_spans[0].tags["name"] == "mytemplate.html"
