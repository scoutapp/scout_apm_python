from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

import scout_apm.celery
from scout_apm.api import Config

from . import celery_app as app


@contextmanager
def app_with_scout(config=None):
    """
    Context manager that configures and installs the Scout plugin for Bottle.

    """
    # Enable Scout by default in tests.
    if config is None:
        config = {"monitor": True}

    # Disable running the agent.
    config["core_agent_launch"] = False

    # Setup according to http://docs.scoutapm.com/#celery
    Config.set(**config)
    scout_apm.celery.install()
    try:
        yield app
    finally:
        scout_apm.celery.uninstall()
        # Reset Scout configuration.
        Config.reset_all()


def test_hello():
    with app_with_scout() as app:
        res = app.hello.apply()
        assert res.result == "Hello World!"


def test_no_monitor():
    # With an empty config, "monitor" defaults to False.
    with app_with_scout({}) as app:
        res = app.hello.apply()
        assert res.result == "Hello World!"
