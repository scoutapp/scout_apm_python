# coding=utf-8

import pytest

from scout_apm.core.config import scout_config
from scout_apm.core.web_requests import (
    create_filtered_path,
    filter_element,
    ignore_path,
)


@pytest.mark.parametrize(
    "path, params, expected",
    [
        ("/", [], "/"),
        ("/foo/", [], "/foo/"),
        ("/", [("bar", "1")], "/?bar=1"),
        ("/", [("bar", "unicØde")], "/?bar=unic%C3%98de"),
        ("/", [("unicØde", "foo")], "/?unic%C3%98de=foo"),
        ("/", [("baz", "2"), ("bar", "1")], "/?bar=1&baz=2"),
        ("/", [("bar", "1"), ("bar", "2")], "/?bar=1&bar=2"),
        ("/", [("password", "hunter2")], "/?password=%5BFILTERED%5D"),
        ("/", [("PASSWORD", "hunter2")], "/?PASSWORD=%5BFILTERED%5D"),
        (
            "/",
            [("password", "hunter2"), ("password", "hunter3")],
            "/?password=%5BFILTERED%5D&password=%5BFILTERED%5D",
        ),
        # Check that if a user mutates the query params to contain non-string
        # types, we cast them to strings.
        ("/", [("bar", 1)], "/?bar=1"),
        ("/", [("bar", None)], "/?bar=None"),
    ],
)
def test_create_filtered_path(path, params, expected):
    assert create_filtered_path(path, params) == expected


@pytest.mark.parametrize(
    "key, value, expected",
    [
        ("bar", "baz", "baz"),
        ("password", "baz", "[FILTERED]"),
        ("bar", {"password": "hunter2"}, {"password": "[FILTERED]"}),
        ("bar", [{"password": "hunter2"}], [{"password": "[FILTERED]"}]),
        ("bar", {"baz"}, {"baz"}),
        (
            "bar",
            ({"password": "hunter2"}, "baz"),
            ({"password": "[FILTERED]"}, "baz"),
        ),
        ("", None, None),
    ],
)
def test_filter_element(key, value, expected):
    assert filter_element(key, value) == expected


@pytest.mark.parametrize("path, params", [("/", []), ("/", [("foo", "ignored")])])
def test_create_filtered_path_path(path, params):
    # If config filtered_params is set to "path", expect we always get the path
    # back
    scout_config.set(uri_reporting="path")
    try:
        assert create_filtered_path(path, params) == path
    finally:
        scout_config.reset_all()


@pytest.mark.parametrize(
    "path, expected",
    [("/health", True), ("/health/foo", True), ("/users", False), ("/", False)],
)
def test_ignore(path, expected):
    scout_config.set(ignore=["/health"])

    try:
        result = ignore_path(path)
    finally:
        scout_config.reset_all()

    assert result == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/health", True),
        ("/health/foo", True),
        ("/api", True),
        ("/api/foo", True),
        ("/users", False),
        ("/", False),
    ],
)
def test_ignore_multiple_prefixes(path, expected):
    scout_config.set(ignore=["/health", "/api"])

    try:
        result = ignore_path(path)
    finally:
        scout_config.reset_all()

    assert result == expected
