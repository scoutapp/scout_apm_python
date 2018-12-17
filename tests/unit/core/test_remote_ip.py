from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.core.remote_ip import RemoteIp


@pytest.mark.parametrize(
    "headers, ip",
    [
        ({"REMOTE_ADDR": "1.1.1.1"}, "1.1.1.1"),
        (
            {"REMOTE_ADDR": "1.1.1.1", "HTTP_X_FORWARDED_FOR": "2.2.2.2,3.3.3.3"},
            "2.2.2.2",
        ),
        ({"REMOTE_ADDR": "1.1.1.1", "HTTP_CLIENT_IP": "2.2.2.2"}, "2.2.2.2"),
        (
            {
                "REMOTE_ADDR": "1.1.1.1",
                "HTTP_X_FORWARDED_FOR": "2.2.2.2,3.3.3.3",
                "HTTP_CLIENT_IP": "4.4.4.4",
            },
            "2.2.2.2",
        ),
        ({}, None),
    ],
)
def test_lookup_from_headers(headers, ip):
    assert RemoteIp.lookup_from_headers(headers) == ip
