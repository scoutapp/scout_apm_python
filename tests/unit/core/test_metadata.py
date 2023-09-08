# coding=utf-8

from types import SimpleNamespace

import pytest

from scout_apm.core.agent.socket import CoreAgentSocketThread
from scout_apm.core.metadata import get_python_packages_versions, report_app_metadata
from tests.compat import mock
from tests.tools import pretend_package_unavailable


@mock.patch.object(CoreAgentSocketThread, "send")
def test_report_app_metadata(mock_send):
    report_app_metadata()

    assert mock_send.call_count == 1
    (command,), kwargs = mock_send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    data = message["ApplicationEvent"]["event_value"]
    assert data["language"] == "python"
    # pytest is installed, since it's running tests right now.
    assert ("pytest", pytest.__version__) in data["libraries"]


@mock.patch.object(CoreAgentSocketThread, "send")
def test_report_app_metadata_no_importlib_metadata(mock_send):
    module_name = "importlib"
    with pretend_package_unavailable(module_name):
        report_app_metadata()

    assert mock_send.call_count == 1
    (command,), kwargs = mock_send.call_args
    assert kwargs == {}

    message = command.message()
    assert message["ApplicationEvent"]["event_type"] == "scout.metadata"
    assert message["ApplicationEvent"]["event_value"]["libraries"] == []


def test_get_python_packages_versions_None_package():
    target = "importlib.metadata.distributions"

    def yielding_nones():
        yield SimpleNamespace(metadata={"Name": "first-package", "Version": "1.0.0"})
        yield SimpleNamespace(metadata={"Name": "second-package", "Version": None})
        yield SimpleNamespace(metadata={"Name": None, "Version": "3.0.0"})

    with mock.patch(target, new=yielding_nones):
        packages = get_python_packages_versions()

    assert packages == [("first-package", "1.0.0"), ("second-package", "Unknown")]
