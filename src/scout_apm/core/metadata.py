# coding=utf-8

import datetime as dt
import sys
from os import getpid

from scout_apm.core.agent.commands import ApplicationEvent, format_dt_for_core_agent
from scout_apm.core.agent.socket import CoreAgentSocketThread
from scout_apm.core.config import scout_config


def report_app_metadata():
    CoreAgentSocketThread.send(
        ApplicationEvent(
            event_type="scout.metadata",
            event_value=get_metadata(),
            source="Pid: " + str(getpid()),
            timestamp=dt.datetime.now(dt.timezone.utc),
        )
    )


def get_metadata():
    data = {
        "language": "python",
        "language_version": "{}.{}.{}".format(*sys.version_info[:3]),
        "server_time": format_dt_for_core_agent(dt.datetime.now(dt.timezone.utc)),
        "framework": scout_config.value("framework"),
        "framework_version": scout_config.value("framework_version"),
        "environment": "",
        "app_server": scout_config.value("app_server"),
        "hostname": scout_config.value("hostname"),
        "database_engine": "",
        "database_adapter": "",
        "application_name": "",
        "libraries": get_python_packages_versions(),
        "paas": "",
        "application_root": scout_config.value("application_root"),
        "scm_subdirectory": scout_config.value("scm_subdirectory"),
        "git_sha": scout_config.value("revision_sha"),
    }
    # Deprecated - see #327:
    data["version"] = data["language_version"]
    return data


def get_python_packages_versions():
    try:
        from importlib.metadata import distributions
    except ImportError:
        # For some reason it is unavailable
        return []

    packages = []
    for distribution in distributions():
        try:
            metadata = distribution.metadata
        except OSError:
            # Python 3.15+ raises MetadataNotFound (a FileNotFoundError) for
            # distributions without a METADATA or PKG-INFO file in their
            # distribution directory, or with an empty one.
            continue
        # Use .get() since Python 3.15+ raises KeyError for missing headers,
        # where earlier versions returned None. Skip distributions without a
        # name, which can happen with a malformed metadata file.
        name = metadata.get("Name")
        if not name:
            continue
        packages.append((name, metadata.get("Version") or "Unknown"))
    return sorted(packages)
