from __future__ import absolute_import

from django.apps import AppConfig
from django.core.signals import request_finished, request_started

from scout_apm_django.instruments.sql import SQLInstrument
from scout_apm_django.instruments.template import TemplateInstrument
from scout_apm_django.instruments.view import ViewInstrument
from scout_apm.tracked_request import TrackedRequest
import scout_apm

import logging


logger = logging.getLogger(__name__)


class DjangoSignals:
    @staticmethod
    def install():
        request_started.connect(DjangoSignals.start_tracked_request,
                                dispatch_uid='request_started_scoutapm')
        request_finished.connect(DjangoSignals.stop_tracked_request,
                                 dispatch_uid='request_stopped_scoutapm')
        logger.debug('Added Django Signals')

    # sender: django.core.handlers.wsgi.WSGIHandler
    # kwargs: 'environ' => { ENV Key => Env Value }
    #         'signal' => <django.dispatch.dispatcher.Signal object at 0x10ed7c470>
    def start_tracked_request(sender, **kwargs):
        # TODO: This is a good spot to extract headers
        operation = 'Django'
        tr = TrackedRequest.instance()
        tr.start_span(operation=operation)
        tr.mark_real_request()

    def stop_tracked_request(sender, **kwargs):
        TrackedRequest.instance().stop_span()


class ScoutApmDjangoConfig(AppConfig):
    name = 'scout_apm'
    verbose_name = 'Scout Apm (Django)'

    def ready(self):
        scout_apm.install()
        DjangoSignals.install()
        SQLInstrument.install()
        TemplateInstrument.install()
        ViewInstrument.install()
