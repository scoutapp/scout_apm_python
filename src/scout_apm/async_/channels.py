# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import wrapt

from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.web_requests import asgi_track_request_data

try:
    from channels.generic.http import AsyncHttpConsumer
except ImportError:  # pragma: no cover
    AsyncHttpConsumer = None


def instrument_channels():
    to_patch = []

    try:
        from channels.generic.http import AsyncHttpConsumer
    except ImportError:  # pragma: no cover
        pass
    else:
        to_patch.append(
            (AsyncHttpConsumer, "http_request", wrapped_async_consumer_method)
        )

    try:
        from channels.generic.websocket import WebsocketConsumer
    except ImportError:  # pragma: no cover
        pass
    else:
        to_patch.append(
            (WebsocketConsumer, "websocket_connect", wrapped_sync_consumer_method)
        )
        to_patch.append(
            (WebsocketConsumer, "websocket_receive", wrapped_sync_consumer_method)
        )

    try:
        from channels.generic.websocket import AsyncWebsocketConsumer
    except ImportError:  # pragma: no cover
        pass
    else:
        to_patch.append(
            (AsyncWebsocketConsumer, "websocket_connect", wrapped_async_consumer_method)
        )
        to_patch.append(
            (AsyncWebsocketConsumer, "websocket_receive", wrapped_async_consumer_method)
        )

    try:
        from channels.generic.websocket import AsyncJsonWebsocketConsumer
    except ImportError:  # pragma: no cover
        pass
    else:
        to_patch.append(
            (AsyncJsonWebsocketConsumer, "receive_json", wrapped_async_consumer_method)
        )

    for class_, method, decorator in to_patch:
        setattr(class_, method, decorator(getattr(class_, method)))


@wrapt.decorator
async def wrapped_async_consumer_method(wrapped, instance, args, kwargs):
    scope = instance.scope

    if scope["type"] not in ("http", "websocket"):
        return await wrapped(*args, **kwargs)

    if scope["type"] == "http":
        message = _extract_message(*args, **kwargs)
        if message.get("more_body"):
            # AsyncHttpConsumer.handle() won't be called yet
            return await wrapped(*args, **kwargs)

    tracked_request = TrackedRequest.instance()
    tracked_request.is_real_request = True

    asgi_track_request_data(scope, tracked_request)
    track_username(scope, tracked_request)

    tracked_request.start_span(operation=name_span(instance, wrapped))
    try:
        return await wrapped(*args, **kwargs)
    except Exception as exc:
        tracked_request.tag("error", "true")
        raise exc
    finally:
        tracked_request.stop_span()


@wrapt.decorator
def wrapped_sync_consumer_method(wrapped, instance, args, kwargs):
    scope = instance.scope

    if scope["type"] not in ("http", "websocket"):
        return wrapped(*args, **kwargs)

    tracked_request = TrackedRequest.instance()
    tracked_request.is_real_request = True

    asgi_track_request_data(scope, tracked_request)
    track_username(scope, tracked_request)

    tracked_request.start_span(operation=name_span(instance, wrapped))
    try:
        return wrapped(*args, **kwargs)
    except Exception as exc:
        tracked_request.tag("error", "true")
        raise exc
    finally:
        tracked_request.stop_span()


def _extract_message(message, *args, **kwargs):
    return message


def track_username(scope, tracked_request):
    user = scope.get("user", None)
    if user is not None:
        try:
            tracked_request.tag("username", user.get_username())
        except Exception:
            pass


def name_span(instance, wrapped):
    return "Controller/{}.{}.{}".format(
        instance.__module__, instance.__class__.__qualname__, wrapped.__name__
    )
