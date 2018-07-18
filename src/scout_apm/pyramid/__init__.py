import scout_apm.core
from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.config import ScoutConfig
from scout_apm.api.context import Context


def includeme(config):
    configs = {}
    pyramid_config = config.get_settings()
    for name in filter(lambda x: x.startswith('SCOUT_'), pyramid_config):
        value = pyramid_config[name]
        clean_name = name.replace('SCOUT_', '').lower()
        configs[clean_name] = value
    ScoutConfig.set(**configs)

    if scout_apm.core.install():
        config.add_tween('scout_apm.pyramid.instruments')


def instruments(handler, registry):
    def scout_tween(request):
        try:
            tr = TrackedRequest.instance()
            span = tr.start_span(operation='Controller/Pyramid')

            # Capture what we can from the request, but never fail
            try:
                Context.add('path', request.path)
                Context.add('user_ip', request.remote_addr)
            except:
                pass

            try:
                response = handler(request)
            except:
                tr.tag('error', 'true')
                raise

            # This happens further down the call chain. So time it starting
            # above, but only name it if it gets to here.
            if request.matched_route is not None:
                tr.mark_real_request()
                span.operation = 'Controller/' + request.matched_route.name

        finally:
            tr.stop_span()

        return response

    return scout_tween

