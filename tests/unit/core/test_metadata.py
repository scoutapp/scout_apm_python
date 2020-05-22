# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import pytest

from scout_apm.core.metadata import get_python_packages_versions, report_app_metadata
from tests.compat import SimpleNamespace, mock
from tests.tools import pretend_package_unavailable


@mock.patch("scout_apm.core.socket.CoreAgentSocketThread.send")
def test_report_app_metadata(send):
    report_app_metadata()

    assert send.call_count == 1
    (command,), kwargs = send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    data = message["ApplicationEvent"]["event_value"]
    assert data["language"] == "python"
    # pytest is installed, since it's running tests right now.
    assert ("pytest", pytest.__version__) in data["libraries"]


@mock.patch("scout_apm.core.socket.CoreAgentSocketThread.send")
def test_report_app_metadata_no_importlib_metadata(send):
    if sys.version_info >= (3, 8):
        module_name = "importlib"
    else:
        module_name = "importlib_metadata"
    with pretend_package_unavailable(module_name):
        report_app_metadata()

    assert send.call_count == 1
    (command,), kwargs = send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    assert message["ApplicationEvent"]["event_value"]["libraries"] == []


def test_get_python_packages_versions_None_package():
    if sys.version_info >= (3, 8):
        target = "importlib.metadata.distributions"
    else:
        target = "importlib_metadata.distributions"

    def yielding_nones():
        yield SimpleNamespace(metadata={"Name": "first-package", "Version": "1.0.0"})
        yield SimpleNamespace(metadata={"Name": "second-package", "Version": None})
        yield SimpleNamespace(metadata={"Name": None, "Version": "3.0.0"})

    with mock.patch(target, new=yielding_nones):
        packages = get_python_packages_versions()

    assert packages == [("first-package", "1.0.0")]
