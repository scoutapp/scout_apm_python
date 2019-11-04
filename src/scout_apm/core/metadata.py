# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import sys
from os import getpid

from scout_apm.core.commands import ApplicationEvent
from scout_apm.core.config import scout_config
from scout_apm.core.socket import CoreAgentSocket


def report_app_metadata():
    CoreAgentSocket.instance().send(
        ApplicationEvent(
            event_type="scout.metadata",
            event_value=get_metadata(),
            source="Pid: " + str(getpid()),
            timestamp=dt.datetime.utcnow(),
        )
    )


def get_metadata():
    data = {
        "language": "python",
        "language_version": "{}.{}.{}".format(*sys.version_info[:3]),
        "server_time": dt.datetime.utcnow().isoformat() + "Z",
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
        import pkg_resources
    except ImportError:
        return []

    return list(
        sorted(
            (distribution.project_name, distribution.version)
            for distribution in pkg_resources.working_set
        )
    )
