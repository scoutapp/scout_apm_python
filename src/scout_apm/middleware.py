# DOCS: https://docs.djangoproject.com/en/1.11/topics/http/middleware/

import logging
from datetime import datetime

# Logging
logger = logging.getLogger(__name__)


class LogTimesMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        t1 = datetime.now()

        response = self.get_response(request)

        t2 = datetime.now()
        seconds_elapsed = (t2 - t1).total_seconds()

        logger.info('Called at: ', request.get_raw_uri())
        logger.info('Seconds for call was: ', seconds_elapsed)
        logger.info('Headers returned were: ', response._headers)

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        logger.info('Process View Callback - Running: %s function %s',
                    view_func.__code__.co_filename, view_func.__code__.co_name)
        return None

    # (only if the view raised an exception)
    def process_exception(self, request, exception):
        logger.info('Raised an exception!')
        return None

    # (only for template responses)
    def process_template_response(self, request, response):
        logger.info('Going to render a template: %s', response.template_name)
        return response
