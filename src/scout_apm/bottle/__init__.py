from __future__ import absolute_import

from bottle import request

import scout_apm.core
from scout_apm.core.context import AgentContext
from scout_apm.core.config import ScoutConfig
from scout_apm.core.tracked_request import TrackedRequest

from scout_apm.api.context import Context


class ScoutPlugin(object):
    def __init__(self):
        self.name = 'scout'
        self.api = 2

    def set_config_from_bottle(self, app):
        scout_config = ScoutConfig()
        bottle_configs = {}
        for k in scout_config.known_keys():
            value = app.config.get("scout.{}".format(k))
            if value is not None and value != '':
                bottle_configs[k] = value
        scout_config.set(**bottle_configs)
        return scout_config

    def setup(self, app):
        self.set_config_from_bottle(app)
        scout_apm.core.install()

    def apply(self, callback, context):
        if AgentContext.instance.config.value('monitor') is not True:
            return callback

        def wrapper(*args, **kwargs):
            try:
                tr = TrackedRequest.instance()
                tr.mark_real_request()
                path = 'Unknown'

                if request.route.name is not None:
                    path = request.route.name
                else:
                    path = request.route.rule

                if path == '/':
                    path = '/home'

                if not path.startswith('/'):
                    path = '/{}'.format(path)

                span = tr.start_span(operation='Controller{}'.format(path))

                try:
                    Context.add('path', path)
                    Context.add('user_ip', request.remote_addr)
                except:
                    pass

                try:
                    response = callback(*args, **kwargs)
                except:
                    tr.tag('error', 'true')
                    raise

            finally:
                tr.stop_span()

            return response
        return wrapper
