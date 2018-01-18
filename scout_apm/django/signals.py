from django.core.signals import request_started, request_finished
from apm.tracked_request import TrackedRequest


class DjangoSignals:
    @staticmethod
    def install():
        request_started.connect(DjangoSignals.start_tracked_request,
                                dispatch_uid='request_started_scoutapm')
        request_finished.connect(DjangoSignals.stop_tracked_request,
                                 dispatch_uid='request_stopped_scoutapm')
        print('Added Django Signals')

    # sender: django.core.handlers.wsgi.WSGIHandler
    # kwargs: 'environ' => { ENV Key => Env Value }
    #         'signal' => <django.dispatch.dispatcher.Signal object at 0x10ed7c470>
    def start_tracked_request(sender, **kwargs):
        # TODO: This is a good spot to extract headers
        operation = 'Django'
        TrackedRequest.instance().start_span(operation=operation)

    def stop_tracked_request(sender, **kwargs):
        TrackedRequest.instance().stop_span()

