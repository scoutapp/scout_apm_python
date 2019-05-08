# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import py

from scout_apm.core.context import AgentContext
from scout_apm.core.metadata import AppMetadata

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch


@patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_report_app_metadata(send):
    AgentContext.build()

    AppMetadata().report()

    assert send.call_count == 1
    (command,), kwargs = send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    # py.test is installed, since it's running tests right now.
    assert ("py", py.version) in message["ApplicationEvent"]["event_value"]["libraries"]


@patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_report_app_metadata_error_getting_data(send):
    AgentContext.build()

    with patch(
        "scout_apm.core.metadata.AppMetadata.get_python_packages_versions",
        side_effect=RuntimeError,
    ):
        AppMetadata().report()

    assert send.call_count == 1
    (command,), kwargs = send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    assert message["ApplicationEvent"]["event_value"] == {}


@patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_report_app_metadata_no_pkg_resources(send):
    AgentContext.build()

    pkg_resources = sys.modules["pkg_resources"]
    sys.modules["pkg_resources"] = None
    try:
        AppMetadata().report()
    finally:
        sys.modules["pkg_resources"] = pkg_resources

    assert send.call_count == 1
    (command,), kwargs = send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    assert message["ApplicationEvent"]["event_value"]["libraries"] == []
