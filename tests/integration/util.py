# coding=utf-8

import pytest

parametrize_filtered_params = pytest.mark.parametrize(
    "params, expected_path",
    [
        ({"foo": "bar"}, "/?foo=bar"),
        ([("foo", "bar"), ("foo", "bar2")], "/?foo=bar&foo=bar2"),
        ({"password": "hunter2"}, "/?password=%5BFILTERED%5D"),
        (
            [("password", "hunter2"), ("password", "hunter3")],
            "/?password=%5BFILTERED%5D&password=%5BFILTERED%5D",
        ),
    ],
)


parametrize_queue_time_header_name = pytest.mark.parametrize(
    "header_name", ["X-Queue-Start", "X-Request-Start"]
)

parametrize_user_ip_headers = pytest.mark.parametrize(
    "headers, client_address, expected",
    # str() calls needed for Python webtest sanity check
    [
        ({}, None, None),
        ({}, str("1.1.1.1"), "1.1.1.1"),
        ({str("x-forwarded-for"): str("1.1.1.1")}, None, "1.1.1.1"),
        ({str("x-forwarded-for"): str("1.1.1.1,2.2.2.2")}, None, "1.1.1.1"),
        ({str("x-forwarded-for"): str("1.1.1.1")}, str("2.2.2.2"), "1.1.1.1"),
        (
            {str("x-forwarded-for"): str("1.1.1.1"), str("client-ip"): str("2.2.2.2")},
            str("3.3.3.3"),
            "1.1.1.1",
        ),
        ({str("client-ip"): str("1.1.1.1")}, None, "1.1.1.1"),
        ({str("client-ip"): str("1.1.1.1,2.2.2.2")}, None, "1.1.1.1"),
        ({str("client-ip"): str("1.1.1.1")}, str("2.2.2.2"), "1.1.1.1"),
        ({str("client-ip"): str("1.1.1.1")}, str("2.2.2.2"), "1.1.1.1"),
    ],
)
