# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import jinja2
import pytest

from scout_apm.instruments.jinja2 import ensure_installed
from tests.compat import mock
from tests.integration.instruments.test_jinja2 import mock_not_attempted


def test_ensure_installed_fail_no_render_async_attribute(caplog):
    mock_template = mock.patch("scout_apm.instruments.jinja2.Template")
    with mock_not_attempted(), mock_template as mocked_template:
        del mocked_template.render_async

        ensure_installed()

        jinja2.Environment()

    assert caplog.record_tuples == [
        (
            "scout_apm.instruments.jinja2",
            logging.DEBUG,
            "Instrumenting Jinja2.",
        )
    ]


@pytest.mark.asyncio
async def test_async_render(tracked_request):
    ensure_installed()
    template = jinja2.Template("Hello {{ name }}!", enable_async=True)

    result = await template.render_async(name="World")

    assert result == "Hello World!"
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Template/Render"
    assert span.tags["name"] is None


@pytest.mark.asyncio
async def test_async_render_name(tracked_request):
    ensure_installed()
    template = jinja2.Template("Hello {{ name }}!", enable_async=True)
    template.name = "mytemplate.html"

    result = await template.render_async(name="World")

    assert result == "Hello World!"
    assert tracked_request.complete_spans[0].tags["name"] == "mytemplate.html"
