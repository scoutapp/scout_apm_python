# coding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import wraps

import django
from django.conf import settings
from django.template.response import TemplateResponse

config = {
    "ALLOWED_HOSTS": ["*"],
    "DATABASES": {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
    },
    "DEBUG_PROPAGATE_EXCEPTIONS": True,
    "ROOT_URLCONF": __name__,
    "SECRET_KEY": "********",
    "TEMPLATES": [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ]
            },
        }
    ],
    "TIME_ZONE": "America/Chicago",
    # Setup as per https://docs.scoutapm.com/#django but *without* the settings
    # - these are temporarily set by app_with_scout() to avoid state leak
    "INSTALLED_APPS": [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.messages",
        "django.contrib.sessions",
        "scout_apm.django",
    ],
}

if django.VERSION > (1, 10):
    config["MIDDLEWARE"] = [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
    ]
else:
    config["MIDDLEWARE_CLASSES"] = [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
    ]


settings.configure(**config)

if True:
    # Old versions of Django, at least 1.8, need settings configured before
    # other bits are imported such as Admin. Hence do the imports here, under
    # an 'if True' to appease isort.
    from django.contrib import admin
    from django.db import connection
    from django.http import HttpResponse
    from django.template import engines
    from django.utils.functional import SimpleLazyObject
    from django.views.generic import View


def home(request):
    return HttpResponse("Welcome home.")


def hello(request):
    return HttpResponse("Hello World!")


def crash(request):
    raise ValueError("BØØM!")  # non-ASCII


class CbvView(View):
    def get(self, request):
        return HttpResponse("Hello getter")


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


def exclaimify_template_response_name(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        response.context_data["name"] = response.context_data["name"] + "!!"
        return response

    return wrapper


@exclaimify_template_response_name
def template_response(request):
    template = engines["django"].from_string(
        "Hello {% block name %}{{ name }}{% endblock %}!"
    )
    context = {"name": "World"}
    return TemplateResponse(request, template, context)


@SimpleLazyObject
def tastypie_api():
    """
    Tastypie API as a lazy object because it needs to import User model which
    can't be done until after django.setup()
    """
    from django.contrib.auth.models import User

    try:
        from tastypie.api import Api as TastypieApi
        from tastypie.resources import ModelResource as TastypieModelResource
    except ImportError:
        return None

    class UserResource(TastypieModelResource):
        class Meta:
            queryset = User.objects.all()
            allowed_methods = ["get"]

    api = TastypieApi(api_name="v1")
    api.register(UserResource())
    return api


@SimpleLazyObject
def urlpatterns():
    """
    URL's as a lazy object because they touch admin.site.urls and that isn't
    ready until django.setup() has been called
    """
    if django.VERSION >= (2, 0):
        from django.urls import include, path

        patterns = [
            path("", home),
            path("hello/", hello),
            path("crash/", crash),
            path("cbv/", CbvView.as_view()),
            path("sql/", sql),
            path("template/", template),
            path("template-response/", template_response),
            path("admin/", admin.site.urls),
        ]
        if tastypie_api:
            patterns.append(path("tastypie-api/", include(tastypie_api.urls)))
        return patterns

    else:
        from django.conf.urls import include, url

        patterns = [
            url(r"^$", home),
            url(r"^hello/$", hello),
            url(r"^crash/$", crash),
            url(r"^cbv/$", CbvView.as_view()),
            url(r"^sql/$", sql),
            url(r"^template/$", template),
            url(r"^template-response/$", template_response),
            url(r"^admin/", admin.site.urls),
        ]
        if tastypie_api:
            patterns.append(url(r"^tastypie-api/", include(tastypie_api.urls)))
        return patterns
