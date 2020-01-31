# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from contextlib import contextmanager

import jinja2

from scout_apm.instruments.jinja2 import ensure_installed
from tests.compat import mock


@contextmanager
def mock_not_attempted():
    not_environment = mock.patch(
        "scout_apm.instruments.jinja2.have_patched_environment_init", new=False
    )
    not_render = mock.patch(
        "scout_apm.instruments.jinja2.have_patched_template_render", new=False
    )
    not_render_async = mock.patch(
        "scout_apm.instruments.jinja2.have_patched_template_render_async", new=False
    )
    with not_environment, not_render, not_render_async:
        yield


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    assert caplog.record_tuples == 2 * [
        (
            "scout_apm.instruments.jinja2",
            logging.INFO,
            "Ensuring Jinja2 instrumentation is installed.",
        )
    ]


def test_ensure_installed_fail_no_template(caplog):
    mock_no_template = mock.patch("scout_apm.instruments.jinja2.Template", new=None)
    with mock_not_attempted(), mock_no_template:
        ensure_installed()

    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.jinja2",
            logging.INFO,
            "Ensuring Jinja2 instrumentation is installed.",
        ),
        (
            "scout_apm.instruments.jinja2",
            logging.INFO,
            "Unable to import jinja2.Template",
        ),
    ]


def test_ensure_installed_fail_no_render_attribute(caplog):
    mock_template = mock.patch("scout_apm.instruments.jinja2.Template")
    with mock_not_attempted(), mock_template as mocked_template:
        # Remove render attribute
        del mocked_template.render

        ensure_installed()

    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples[0] == (
        "scout_apm.instruments.jinja2",
        logging.INFO,
        "Ensuring Jinja2 instrumentation is installed.",
    )
    logger, level, message = caplog.record_tuples[1]
    assert logger == "scout_apm.instruments.jinja2"
    assert level == logging.WARNING
    assert message.startswith(
        "Unable to instrument jinja2.Template.render: AttributeError"
    )


def test_render(tracked_request):
    ensure_installed()
    template = jinja2.Template("Hello {{ name }}!")

    result = template.render(name="World")

    assert result == "Hello World!"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Template/Render"
    assert span.tags["name"] is None


def test_render_template_name(tracked_request):
    ensure_installed()
    template = jinja2.Template("Hello {{ name }}!")
    template.name = "mytemplate.html"

    result = template.render(name="World")

    assert result == "Hello World!"
    assert tracked_request.complete_spans[0].tags["name"] == "mytemplate.html"
