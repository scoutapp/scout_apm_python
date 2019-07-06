# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import django
from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.template import engines

config = {
    "ALLOWED_HOSTS": ["*"],
    "DATABASES": {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
    },
    # Enable the following for debugging exceptions:
    # "DEBUG": True,
    # "DEBUG_PROPAGATE_EXCEPTIONS": True,
    "ROOT_URLCONF": __name__,
    "SECRET_KEY": "********",
    "TEMPLATES": [{"BACKEND": "django.template.backends.django.DjangoTemplates"}],
    "TIME_ZONE": "America/Chicago",
    # Setup as per https://docs.scoutapm.com/#django but *without* the settings
    # - these are temporarily set by app_with_scout() to avoid state leak
    "INSTALLED_APPS": ["scout_apm.django"],
}

if django.VERSION > (1, 10):
    config["MIDDLEWARE"] = []
else:
    config["MIDDLEWARE_CLASSES"] = []


settings.configure(**config)


def home(request):
    return HttpResponse("Welcome home.")


def hello(request):
    return HttpResponse("Hello World!")


def crash(request):
    raise ValueError("BØØM!")  # non-ASCII


def sql(request):
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS test(item)")
        cursor.executemany(
            "INSERT INTO test(item) VALUES(%s)", [("Hello",), ("World!",)]
        )
        cursor.execute("SELECT item from test")
        result = " ".join(item for (item,) in cursor.fetchall())
    return HttpResponse(result)


def template(request):
    template = engines["django"].from_string(
        "Hello {% block name %}{{ name }}{% endblock %}!"
    )
    context = {"name": "World"}
    return HttpResponse(template.render(context))


try:
    from django.urls import path

    urlpatterns = [
        path("", home),
        path("hello/", hello),
        path("crash/", crash),
        path("sql/", sql),
        path("template/", template),
    ]
except ImportError:  # Django < 2.0
    from django.conf.urls import url

    urlpatterns = [
        url(r"^$", home),
        url(r"^hello/$", hello),
        url(r"^crash/$", crash),
        url(r"^sql/$", sql),
        url(r"^template/$", template),
    ]
