# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.core.web_requests import create_filtered_path


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
