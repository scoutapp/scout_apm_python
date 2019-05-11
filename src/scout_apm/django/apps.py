# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.apps import AppConfig
from django.conf import settings

import scout_apm.core
from scout_apm.core.config import ScoutConfig
from scout_apm.django.instruments.sql import install_sql_instrumentation
from scout_apm.django.instruments.template import install_template_instrumentation

logger = logging.getLogger(__name__)


class ScoutApmDjangoConfig(AppConfig):
    name = "scout_apm"
    verbose_name = "Scout Apm (Django)"

    def ready(self):
        self.copy_config()

        # Finish installing the agent. If the agent isn't installed for any
        # reason, return without installing instruments
        installed = scout_apm.core.install()
        if not installed:
            return

        self.install_middleware()

        # Setup Instruments
        install_sql_instrumentation()
        install_template_instrumentation()

    def copy_config(self):
        configs = {}
        if getattr(settings, "BASE_DIR", None) is not None:
            configs["application_root"] = settings.BASE_DIR
        for name in dir(settings):
            if name.startswith("SCOUT_"):
                value = getattr(settings, name)
                clean_name = name.replace("SCOUT_", "").lower()
                configs[clean_name] = value
        ScoutConfig.set(**configs)

    def install_middleware(self):
        """
        Attempts to insert the ScoutApm middleware as the first middleware
        (first on incoming requests, last on outgoing responses).
        """
        from django.conf import settings

        # If MIDDLEWARE is set, update that, with handling of tuple vs array forms
        if getattr(settings, "MIDDLEWARE", None) is not None:
            timing_middleware = "scout_apm.django.middleware.MiddlewareTimingMiddleware"
            view_middleware = "scout_apm.django.middleware.ViewTimingMiddleware"

            if isinstance(settings.MIDDLEWARE, tuple):
                if timing_middleware not in settings.MIDDLEWARE:
                    settings.MIDDLEWARE = (timing_middleware,) + settings.MIDDLEWARE
                if view_middleware not in settings.MIDDLEWARE:
                    settings.MIDDLEWARE = settings.MIDDLEWARE + (view_middleware,)
            else:
                if timing_middleware not in settings.MIDDLEWARE:
                    settings.MIDDLEWARE.insert(0, timing_middleware)
                if view_middleware not in settings.MIDDLEWARE:
                    settings.MIDDLEWARE.append(view_middleware)

        # Otherwise, we're doing old style middleware, do the same thing with
        # the same handling of tuple vs array forms
        else:
            timing_middleware = (
                "scout_apm.django.middleware.OldStyleMiddlewareTimingMiddleware"
            )
            view_middleware = "scout_apm.django.middleware.OldStyleViewMiddleware"

            if isinstance(settings.MIDDLEWARE_CLASSES, tuple):
                if timing_middleware not in settings.MIDDLEWARE_CLASSES:
                    settings.MIDDLEWARE_CLASSES = (
                        timing_middleware,
                    ) + settings.MIDDLEWARE_CLASSES

                if view_middleware not in settings.MIDDLEWARE_CLASSES:
                    settings.MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES + (
                        view_middleware,
                    )
            else:
                if timing_middleware not in settings.MIDDLEWARE_CLASSES:
                    settings.MIDDLEWARE_CLASSES.insert(0, timing_middleware)
                if view_middleware not in settings.MIDDLEWARE_CLASSES:
                    settings.MIDDLEWARE_CLASSES.append(view_middleware)
