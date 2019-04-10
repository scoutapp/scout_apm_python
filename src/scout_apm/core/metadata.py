from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
from datetime import datetime
from os import getpid

from scout_apm.core.commands import ApplicationEvent
from scout_apm.core.context import AgentContext

logger = logging.getLogger(__name__)


class AppMetadata(object):
    @classmethod
    def report(cls):
        event = ApplicationEvent()
        event.event_value = cls.data()
        event.event_type = "scout.metadata"
        event.timestamp = datetime.utcnow()
        event.source = "Pid: " + str(getpid())
        AgentContext.socket().send(event)

    @classmethod
    def data(cls):
        config = AgentContext.instance.config
        try:
            data = {
                "language": "python",
                "version": "{}.{}.{}".format(*sys.version_info[:3]),
                "server_time": datetime.utcnow().isoformat() + "Z",
                "framework": config.value("framework"),
                "framework_version": config.value("framework_version"),
                "environment": "",
                "app_server": config.value("app_server"),
                "hostname": config.value("hostname"),
                "database_engine": "",  # Detected
                "database_adapter": "",  # Raw
                "application_name": "",  # Environment.application_name,
                "libraries": cls.get_python_packages_versions(),
                "paas": "",
                "application_root": config.value("application_root"),
                "scm_subdirectory": config.value("scm_subdirectory"),
                "git_sha": config.value("revision_sha"),
            }
        except Exception as e:
            logger.debug("Exception in AppMetadata: %r", e)
            data = {}

        return data

    @classmethod
    def get_python_packages_versions(cls):
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
