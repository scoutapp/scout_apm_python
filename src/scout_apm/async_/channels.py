# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial

import wrapt

from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import asgi_track_request_data

try:
    from channels.generic.http import AsyncHttpConsumer
except ImportError:  # pragma: no cover
    AsyncHttpConsumer = None


def instrument_channels():
    return
    try:
        from channels.generic.http import AsyncHttpConsumer
    except ImportError:  # pragma: no cover
        pass
    else:
        AsyncHttpConsumer.http_request = wrapped_http_request(
            AsyncHttpConsumer.http_request
        )

    try:
        from channels.generic.websocket import WebsocketConsumer
    except ImportError:  # pragma: no cover
        pass
    else:
        WebsocketConsumer.websocket_connect = wrapped_websocket_connect(
            WebsocketConsumer.websocket_connect
        )


@wrapt.decorator
async def wrapped_http_request(wrapped, instance, args, kwargs):
    message = _extract_message(*args, **kwargs)
    scope = instance.scope

    if message.get("more_body"):
        # handle() won't be called yet
        return await wrapped(*args, **kwargs)

    tracked_request = TrackedRequest.instance()
    tracked_request.is_real_request = True

    asgi_track_request_data(scope, tracked_request)

    user = scope.get("user", None)
    if user is not None:
        try:
            tracked_request.tag("username", user.get_username())
        except Exception:
            pass

    tracked_request.start_span(
        operation="Controller/{}.{}".format(
            instance.__module__, instance.__class__.__qualname__
        )
    )

    try:
        return await wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()


def _extract_message(message, *args, **kwargs):
    return message


@wrapt.decorator
def wrapped_websocket_connect(wrapped, instance, args, kwargs):
    scope = instance.scope

    tracked_request = TrackedRequest.instance()
    tracked_request.is_real_request = True

    asgi_track_request_data(scope, tracked_request)

    user = scope.get("user", None)
    if user is not None:
        try:
            tracked_request.tag("username", user.get_username())
        except Exception:
            pass

    tracked_request.start_span(
        operation="Controller/{}.{}.websocket_connect".format(
            instance.__module__, instance.__class__.__qualname__
        )
    )

    try:
        return wrapped(*args, **kwargs)
    finally:
        tracked_request.stop_span()


class ScoutMiddleware:
    def __init__(self, inner):
        # Channels is ASGI 2 at time of writing
        # https://github.com/django/channels/issues/1316
        # asgiref.compatibility may be of use?
        # https://github.com/django/asgiref/blob/master/asgiref/compatibility.py
        self.inner = inner

    def __call__(self, scope):
        inner_instance = self.inner(scope)
        return partial(self.coroutine_call, inner_instance, scope)

    async def coroutine_call(self, inner_instance, scope, receive, send):
        # TODO - filter to only recognized HTTP + WS calls
        tracked_request = TrackedRequest.instance()
        tracked_request.is_real_request = True

        asgi_track_request_data(scope, tracked_request)

        user = scope.get("user", None)
        if user is not None:
            try:
                tracked_request.tag("username", user.get_username())
            except Exception:
                pass

        tracked_request.start_span(
            operation="Controller/{}.{}".format(
                "foo",
                "bar"
                # TODO: when monkey patching the consumer it was easy to fdin
                # controller name, as an outer middleware it's not
                # but maybe we can with stack inspetion to see if sending from
                # a subclass of the known generic consumer classes?
                # instance.__module__, instance.__class__.__qualname__
            )
        )

        try:
            return await inner_instance(receive, send)
        finally:
            tracked_request.stop_span()
