from __future__ import absolute_import

# Python Modules
from datetime import datetime
import logging
from os import getpid
import sys


# Scout APM
from scout_apm.core.context import AgentContext
from scout_apm.core.commands import ApplicationEvent

logger = logging.getLogger(__name__)


class AppMetadata():
    @classmethod
    def report(cls):
        event = ApplicationEvent()
        event.event_value = cls.data()
        event.event_type = 'scout.metadata'
        event.timestamp = datetime.utcnow()
        event.source = 'Pid: ' + str(getpid())
        AgentContext.socket().send(event)

    @classmethod
    def data(cls):
        data = {}
        version_tuple = sys.version_info
        try:
            data = {'language':          'python',
                    'version':           '{}.{}.{}'.format(version_tuple[0],
                                                           version_tuple[1],
                                                           version_tuple[2]),
                    'server_time':        datetime.utcnow().isoformat() + 'Z',
                    'framework':          AgentContext.instance.config.value('framework'),
                    'framework_version':  AgentContext.instance.config.value('framework_version'),
                    'environment':        '',
                    'app_server':         AgentContext.instance.config.value('app_server'),
                    'hostname':           AgentContext.instance.config.value('hostname'),
                    'database_engine':    '',  # Detected
                    'database_adapter':   '',  # Raw
                    'application_name':   '',  # Environment.application_name,
                    'libraries':          cls.get_python_packages_versions(),
                    'paas':               '',
                    'application_root':   AgentContext.instance.config.value('application_root'),
                    'git_sha':            AgentContext.instance.config.value('revision_sha')}
        except Exception as e:
            logger.debug('Exception in AppMetadata: %s', repr(e))

        return data

    @classmethod
    def get_python_packages_versions(cls):
        try:
            import pkg_resources
        except ImportError:
            return []

        return list(sorted(
            (distribution.project_name, distribution.version)
            for distribution in pkg_resources.working_set
        ))
