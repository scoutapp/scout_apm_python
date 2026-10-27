# coding=utf-8

import sys
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


def test_get_python_packages_versions_missing_keys():
    # Python 3.15+ raises KeyError for missing metadata headers.
    target = "importlib.metadata.distributions"

    def yielding_missing_keys():
        yield SimpleNamespace(metadata={"Name": "first-package", "Version": "1.0.0"})
        yield SimpleNamespace(metadata={"Name": "second-package"})
        yield SimpleNamespace(metadata={"Version": "3.0.0"})

    with mock.patch(target, new=yielding_missing_keys):
        packages = get_python_packages_versions()

    assert packages == [("first-package", "1.0.0"), ("second-package", "Unknown")]


def test_get_python_packages_versions_metadata_not_found():
    # Python 3.15+ raises MetadataNotFound, a FileNotFoundError subclass, for
    # distributions without a metadata file.
    target = "importlib.metadata.distributions"

    class NoMetadataDistribution:
        @property
        def metadata(self):
            raise FileNotFoundError("No package metadata was found.")

    def yielding_no_metadata():
        yield SimpleNamespace(metadata={"Name": "first-package", "Version": "1.0.0"})
        yield NoMetadataDistribution()

    with mock.patch(target, new=yielding_no_metadata):
        packages = get_python_packages_versions()

    assert packages == [("first-package", "1.0.0")]


def test_get_python_packages_versions_broken_distributions(tmp_path):
    (tmp_path / "no_name-1.0.dist-info").mkdir()
    (tmp_path / "no_name-1.0.dist-info" / "METADATA").write_text("Version: 1.0\n")
    (tmp_path / "blank-1.0.dist-info").mkdir()
    (tmp_path / "blank-1.0.dist-info" / "METADATA").write_text("\n")
    (tmp_path / "empty-1.0.dist-info").mkdir()
    (tmp_path / "empty-1.0.dist-info" / "METADATA").write_text("")
    (tmp_path / "missing-1.0.dist-info").mkdir()
    (tmp_path / "no_version-1.0.dist-info").mkdir()
    (tmp_path / "no_version-1.0.dist-info" / "METADATA").write_text(
        "Name: no-version\n"
    )
    (tmp_path / "latin1-1.0.dist-info").mkdir()
    (tmp_path / "latin1-1.0.dist-info" / "METADATA").write_bytes(
        b"Name: latin1\nVersion: 1.0\nAuthor: Jos\xe9\n"
    )

    with mock.patch("sys.path", [str(tmp_path)] + sys.path):
        packages = get_python_packages_versions()

    names = [name for name, _ in packages]
    assert all(names)
    assert "latin1" not in names
    assert ("no-version", "Unknown") in packages
    assert ("pytest", pytest.__version__) in packages


def test_get_python_packages_versions_metadata_without_get():
    # PackageMetadata only gained get() in Python 3.12, so third-party
    # Distribution classes may return objects without it.
    target = "importlib.metadata.distributions"

    def yielding_no_get():
        yield SimpleNamespace(metadata={"Name": "first-package", "Version": "1.0.0"})
        yield SimpleNamespace(metadata=object())

    with mock.patch(target, new=yielding_no_get):
        packages = get_python_packages_versions()

    assert packages == [("first-package", "1.0.0")]


def test_get_python_packages_versions_broken_finder():
    class BrokenFinder:
        def find_spec(self, *args, **kwargs):
            return None

        def find_distributions(self, *args, **kwargs):
            raise RuntimeError("boom")

    with mock.patch("sys.meta_path", sys.meta_path + [BrokenFinder()]):
        packages = get_python_packages_versions()

    # Distributions from finders before the broken one are still reported.
    assert ("pytest", pytest.__version__) in packages
