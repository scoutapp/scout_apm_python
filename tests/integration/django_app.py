# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.db import connection
from django.http import HttpResponse
from django.template import engines

settings.configure(
    ALLOWED_HOSTS=["*"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    DEBUG=True,
    ROOT_URLCONF=__name__,
    SECRET_KEY="********",
    TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates"}],
    TIME_ZONE="America/Chicago",
)


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


app = get_wsgi_application()
