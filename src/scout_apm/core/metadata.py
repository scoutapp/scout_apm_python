from __future__ import absolute_import

# Python Modules
from datetime import datetime
import logging
from os import getpid
import pip
import sys


# Scout APM
from scout_apm.core.context import AgentContext
from scout_apm.core.commands import ApplicationEvent
# from scout_apm.environment import Environment

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
                    'framework':          '',
                    'framework_version':  '',
                    'environment':        '',
                    'app_server':         '',
                    'hostname':           '',  # Environment.hostname,
                    'database_engine':    '',  # Detected
                    'database_adapter':   '',  # Raw
                    'application_name':   '',  # Environment.application_name,
                    'libraries':          cls.package_list(),
                    'paas':               '',
                    'git_sha':            ''}  # Environment.git_revision_sha()}
        except Exception as e:
            logger.debug('Exception in AppMetadata: %s', repr(e))

        return data

    @classmethod
    def package_list(cls):
        packages = []
        try:
            for pkg_dist in [p for p in pip._vendor.pkg_resources.working_set]:
                try:
                    p_split = str(pkg_dist).split()
                    packages.append([p_split[0], p_split[1]])
                except Exception as e:
                    logger.debug('Exception while reading packages: %s', repr(e))
                    continue
        except Exception as e:
            logger.debug('Exception while getting pkg_resources: %s', repr(e))
        return packages
