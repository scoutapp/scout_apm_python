# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

import cherrypy
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.cherrypy import ScoutPlugin


@contextmanager
def app_with_scout(scout_config=None):
    """
    Context manager that configures and installs the Scout plugin for CherryPy.
    """
    if scout_config is None:
        scout_config = {}

    scout_config["core_agent_launch"] = False
    scout_config.setdefault("monitor", True)
    Config.set(**scout_config)

    # # Disable Flask's error page to improve debugging
    # config.setdefault("PROPAGATE_EXCEPTIONS", True)

    class Views(object):
        @cherrypy.expose
        def index(self):
            return "Welcome home."

    app = cherrypy.Application(Views(), "/", config=None)
    plugin = ScoutPlugin(cherrypy.engine)
    plugin.subscribe()

    try:
        yield app
    finally:
        plugin.unsubscribe()
        Config.reset_all()


def test_home(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert len(tracked_request.complete_spans) == 1
    assert tracked_request.tags["path"] == "/"
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_cherrypy.index"


def test_home_ignored(tracked_requests):
    with app_with_scout(scout_config={"ignore": "/"}) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert tracked_requests == []
