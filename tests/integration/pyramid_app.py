# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from pyramid.config import Configurator
from pyramid.response import Response


def home(request):
    return Response("Welcome home.")


def hello(request):
    return Response("Hello World!")


def crash(request):
    raise ValueError("BØØM!")  # non-ASCII


@contextmanager
def app_configurator():
    with Configurator() as configurator:
        configurator.add_route("home", "/")
        configurator.add_view(home, route_name="home", request_method="GET")
        configurator.add_route("hello", "/hello/")
        configurator.add_view(hello, route_name="hello")
        configurator.add_route("crash", "/crash/")
        configurator.add_view(crash, route_name="crash")
        yield configurator


with app_configurator() as configurator:
    app = configurator.make_wsgi_app()
