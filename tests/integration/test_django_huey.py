# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from contextlib import contextmanager

from django.core.management import call_command
from django.test.utils import override_settings
from huey import MemoryHuey

from tests.integration import django_app

from tests.integration.test_django import app_with_scout as django_app_with_scout


@contextmanager
def app_with_scout(**settings):
    # https://huey.readthedocs.io/en/latest/django.html
    installed_apps = django_app.config["INSTALLED_APPS"] + ["huey.contrib.djhuey"]
    huey = MemoryHuey(immediate=True)
    install_huey = override_settings(
        INSTALLED_APPS=installed_apps,
        HUEY=huey,
    )
    with django_app_with_scout(**settings) as app, install_huey:
        @huey.task()
        def hello():
            return "Hello World!"

        App = namedtuple("App", ["app", "huey", "hello"])
        yield App(app, huey, hello)


def test_basic_task(tracked_requests):
    with app_with_scout() as app:
        result = app.hello()
        call_command('run_huey')
        value = result(blocking=True, timeout=1)

    assert value == "Hello World!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    assert "task_id" in tracked_request.tags
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "Job/tests.integration.test_huey.hello"
