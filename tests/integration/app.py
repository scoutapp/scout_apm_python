#!/usr/bin/env python
# coding=utf-8

"""
Test application that proxies requests to various frameworks.

Run it with Python's built-in WSGI server or with a third-party server:

    $ PYTHONPATH=. tests/integration/app.py
    $ gunicorn tests.integration.app:app
    $ waitress-serve tests.integration.app:app

Configure it with the SCOUT_MONITOR, SCOUT_KEY, and SCOUT_NAME env variables.

"""

import scout_apm.api
from tests.integration import test_bottle, test_django, test_flask, test_pyramid

# Launch Scout APM agent
print("Installing Scout APM")
scout_apm.api.install()

# Create instrumented sub-apps
SUB_APPS = {}
with test_bottle.app_with_scout() as app:
    SUB_APPS["/bottle"] = app
with test_django.app_with_scout() as app:
    SUB_APPS["/django"] = app
with test_flask.app_with_scout() as app:
    SUB_APPS["/flask"] = app
with test_pyramid.app_with_scout() as app:
    SUB_APPS["/pyramid"] = app


def app(environ, start_response):
    path = environ["PATH_INFO"]

    if path == "/":
        start_response("200 OK", [("Content-Type", "text/html")])
        return [
            b"""<DOCTYPE html>
<html>
<head>
    <title>Scout APM integration tests</title>
    <style>
        html { font-family: sans-serif; }
        body { margin: 2em auto; max-width: 1024px; }
        h1 { text-align: center; }
        .apps { display: flex; justify-content: space-evenly; }
    </style>
</head>
<body>
    <h1>Scout APM integration tests</h1>
    <div class="apps">
        <div class="app">
            <h2>Bottle</h2>
            <ul>
                <li><a href="/bottle/">Home</a></li>
                <li><a href="/bottle/hello/">Hello</a></li>
                <li><a href="/bottle/crash/">Crash</a></li>
            </ul>
        </div>
        <div class="app">
            <h2>Django</h2>
            <ul>
                <li><a href="/django/">Home</a></li>
                <li><a href="/django/hello/">Hello</a></li>
                <li><a href="/django/crash/">Crash</a></li>
                <li><a href="/django/sql/">SQL</a></li>
                <li><a href="/django/template/">Template</a></li>
            </ul>
        </div>
        <div class="app">
            <h2>Flask</h2>
            <ul>
                <li><a href="/flask/">Home</a></li>
                <li><a href="/flask/hello/">Hello</a></li>
                <li><a href="/flask/crash/">Crash</a></li>
            </ul>
        </div>
        <div class="app">
            <h2>Pyramid</h2>
            <ul>
                <li><a href="/pyramid/">Home</a></li>
                <li><a href="/pyramid/hello/">Hello</a></li>
                <li><a href="/pyramid/crash/">Crash</a></li>
            </ul>
        </div>
    </div>
</body>
</html>
"""
        ]

    for prefix, sub_app in SUB_APPS.items():
        if path.startswith(prefix + "/"):
            environ = environ.copy()
            environ.update(
                {
                    "PATH_INFO": environ["PATH_INFO"][len(prefix) :],
                    "SCRIPT_NAME": environ["SCRIPT_NAME"] + prefix,
                }
            )
            return sub_app(environ, start_response)

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not found"]


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    print("Serving on http://0.0.0.0:8080")
    make_server("", 8080, app).serve_forever()
