# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from nameko.web.handlers import http
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.nameko import ScoutReporter


@contextmanager
def app_with_scout(container_factory, nameko_config=None, scout_config=None):
    """
    Context manager that yields a fresh Nameko WSGI app with Scout configured.
    """
    if scout_config is None:
        scout_config = {"monitor": True}
    scout_config["core_agent_launch"] = False

    # Nameko setup
    class Service(object):
        name = "myservice"

        scout = ScoutReporter()

        @http("GET", "/")
        def resource(self, request):
            return "Welcome home."

    if nameko_config is None:
        nameko_config = {}
    container = container_factory(Service, nameko_config)
    container.start()
    # A bit of introspection to look inside the container and pull out the WSGI
    # app
    app = list(container.subextensions)[0].get_wsgi_app()

    # N.B. We're sidestepping the Nameko testing conventions
    # (https://docs.nameko.io/en/stable/testing.html) to make our tests more
    # uniform between frameworks

    try:
        yield app
    finally:
        Config.reset_all()


def test_home(container_factory, tracked_requests):
    with app_with_scout(container_factory) as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == "Welcome home."
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    # assert tracked_request.tags["path"] == "/"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Test"
