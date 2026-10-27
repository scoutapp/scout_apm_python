# coding=utf-8

import datetime as dt
import logging
import sys
from os import getpid

from scout_apm.core.agent.commands import ApplicationEvent, format_dt_for_core_agent
from scout_apm.core.agent.socket import CoreAgentSocketThread
from scout_apm.core.config import scout_config

logger = logging.getLogger(__name__)


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

    # Errors are deliberately caught broadly here: a broken installed package
    # shouldn't stop the app from starting.
    packages = []
    try:
        for distribution in distributions():
            try:
                metadata = distribution.metadata
                # Use .get() since Python 3.15+ raises KeyError for missing
                # headers. Python 3.12-3.14 return None but emit a
                # DeprecationWarning, which fails under -W error.
                name = metadata.get("Name")
                version = metadata.get("Version")
            except Exception as exc:
                # Known cases are MetadataNotFound (a FileNotFoundError) on
                # Python 3.15+ for a missing or empty METADATA/PKG-INFO file,
                # UnicodeDecodeError for a non-UTF-8 one, and whatever custom
                # Distribution classes may raise.
                logger.debug(
                    "Skipping distribution with unreadable metadata: %r",
                    exc,
                    exc_info=exc,
                )
                continue
            # Skip distributions without a name, which can happen with a
            # malformed metadata file.
            if not name:
                continue
            packages.append((name, version or "Unknown"))
    except Exception as exc:
        # Listing distributions can itself fail, e.g. a custom finder on
        # sys.meta_path raising. Report what was found before the error.
        logger.debug("Error listing installed distributions: %r", exc, exc_info=exc)
    return sorted(packages)
