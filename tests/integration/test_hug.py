# coding=utf-8
"""
Because the Hug integration is based on the Falcon one, we test only the
extras here, specifically the transaction naming.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

import pytest
from webtest import TestApp

from scout_apm.api import Config
from scout_apm.compat import kwargs_only


try:
    import hug
except ImportError:
    hug = None
else:
    from scout_apm.hug import integrate_scout


if hug is not None:
    # Hug doesn't (seem to) support individual apps, since they're automatically
    # module scoped, so use a single module level app:

    @hug.get("/")
    def home():
        return "Welcome home."


skip_if_hug_unavailable = pytest.mark.skipif(hug is None, reason="Hug isn't available")
pytestmark = [skip_if_hug_unavailable]

scout_integrated = False


@contextmanager
@kwargs_only
def app_with_scout(scout_config=None):
    """
    Context manager that yields the global Hug app with Scout configured.
    """
    global scout_integrated

    if scout_config is None:
        scout_config = {}

    scout_config["core_agent_launch"] = False
    scout_config.setdefault("monitor", True)
    Config.set(**scout_config)

    if not scout_integrated:
        integrate_scout(__name__, config={})
        scout_integrated = True

    try:
        # Hug attaches magic names to the current module when you use the @hug
        # decorators, we're interested in the WSGI app:
        yield __hug_wsgi__  # noqa: F821
    finally:
        Config.reset_all()


def test_home(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/")

    assert response.status_int == 200
    assert response.text == '"Welcome home."'
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert tracked_request.tags["path"] == "/"
    assert tracked_request.active_spans == []
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Controller/tests.integration.test_hug.home"
