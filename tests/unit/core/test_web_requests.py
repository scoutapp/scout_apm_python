# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.core.context import AgentContext
from scout_apm.core.web_requests import create_filtered_path


@pytest.fixture(autouse=True)
def force_context():
    # Since this function accesses the context, it needs to always be built
    # TODO: remove when moving to a sensible singleton pattern
    AgentContext.build()


@pytest.mark.parametrize(
    "path, params, expected",
    [
        ("/", [], "/"),
        ("/foo/", [], "/foo/"),
        ("/", [("bar", "1")], "/?bar=1"),
        ("/", [("baz", 2), ("bar", "1")], "/?bar=1&baz=2"),
        ("/", [("bar", "1"), ("bar", "2")], "/?bar=1&bar=2"),
        ("/", [("password", "hunter2")], "/?password=%5BFILTERED%5D"),
        ("/", [("PASSWORD", "hunter2")], "/?PASSWORD=%5BFILTERED%5D"),
        (
            "/",
            [("password", "hunter2"), ("password", "hunter3")],
            "/?password=%5BFILTERED%5D&password=%5BFILTERED%5D",
        ),
    ],
)
def test_create_filtered_path(path, params, expected):
    assert create_filtered_path(path, params) == expected


@pytest.mark.parametrize("path, params", [("/", []), ("/", [("foo", "ignored")])])
def test_create_filtered_path_path(path, params):
    # If config filtered_params is set to "path", expect we always get the path
    # back
    AgentContext.instance.config.set(uri_reporting="path")
    try:
        assert create_filtered_path(path, params) == path
    finally:
        AgentContext.instance.config.reset_all()
