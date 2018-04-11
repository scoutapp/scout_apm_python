from __future__ import absolute_import

from django.apps import AppConfig

from scout_apm.django.instruments.sql import SQLInstrument
from scout_apm.django.instruments.template import TemplateInstrument
from scout_apm.django.config import ConfigAdapter
import scout_apm.core

import logging


logger = logging.getLogger(__name__)


class ScoutApmDjangoConfig(AppConfig):
    name = 'scout_apm'
    verbose_name = 'Scout Apm (Django)'

    def ready(self):
        # Copy django configuration to scout_apm's config
        ConfigAdapter.install()

        # Finish installing the agent. If the agent isn't installed for any
        # reason, return without installing instruments
        installed = scout_apm.core.install()
        if installed is False:
            return

        self.install_middleware()

        # Setup Instruments
        SQLInstrument.install()
        TemplateInstrument.install()

    def install_middleware(self):
        """
        Attempts to insert the ScoutApm middleware as the first middleware
        (first on incoming requests, last on outgoing responses).
        """
        from django.conf import settings

        if isinstance(settings.MIDDLEWARE, tuple):
            settings.MIDDLEWARE = (
                ('scout_apm.django.middleware.MiddlewareTimingMiddleware', ) +
                settings.MIDDLEWARE +
                ('scout_apm.django.middleware.ViewTimingMiddleware', ))
        else:
            settings.MIDDLEWARE.insert(0, 'scout_apm.django.middleware.MiddlewareTimingMiddleware')
            settings.MIDDLEWARE.append('scout_apm.django.middleware.ViewTimingMiddleware')

