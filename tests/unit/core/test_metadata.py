# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import py

from scout_apm.core.metadata import AppMetadata
from tests.compat import mock
from tests.tools import pretend_package_unavailable


@mock.patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_report_app_metadata(send):
    AppMetadata().report()

    assert send.call_count == 1
    (command,), kwargs = send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    # py.test is installed, since it's running tests right now.
    assert ("py", py.version) in message["ApplicationEvent"]["event_value"]["libraries"]


@mock.patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_report_app_metadata_error_getting_data(send):
    with mock.patch(
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


@mock.patch("scout_apm.core.socket.CoreAgentSocket.send")
def test_report_app_metadata_no_pkg_resources(send):
    with pretend_package_unavailable("pkg_resources"):
        AppMetadata().report()

    assert send.call_count == 1
    (command,), kwargs = send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    assert message["ApplicationEvent"]["event_value"]["libraries"] == []
