# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

parametrize_user_ip_headers = pytest.mark.parametrize(
    "headers, extra_environ, expected",
    [
        ({}, {}, None),
        ({}, {"REMOTE_ADDR": "1.1.1.1"}, "1.1.1.1"),
        ({"x-forwarded-for": "1.1.1.1"}, {}, "1.1.1.1"),
        ({"x-forwarded-for": "1.1.1.1,2.2.2.2"}, {}, "1.1.1.1"),
        ({"x-forwarded-for": "1.1.1.1"}, {"REMOTE_ADDR": "2.2.2.2"}, "1.1.1.1"),
        (
            {"x-forwarded-for": "1.1.1.1", "client-ip": "2.2.2.2"},
            {"REMOTE_ADDR": "3.3.3.3"},
            "1.1.1.1",
        ),
        ({"client-ip": "1.1.1.1"}, {}, "1.1.1.1"),
        ({"client-ip": "1.1.1.1,2.2.2.2"}, {}, "1.1.1.1"),
        ({"client-ip": "1.1.1.1"}, {"REMOTE_ADDR": "2.2.2.2"}, "1.1.1.1"),
        ({"client-ip": "1.1.1.1"}, {"REMOTE_ADDR": "2.2.2.2"}, "1.1.1.1"),
    ],
)
