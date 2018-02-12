# DOCS: https://docs.djangoproject.com/en/1.11/topics/http/middleware/

from datetime import datetime
import logging
import pdb

#  from .instruments.sql import SQLInstrument;
#  from .instruments.template import TemplateInstrument;
#  from .instruments.view import ViewInstrument;
#  SQLInstrument.init()
#  TemplateInstrument.init()
#  ViewInstrument.init()

# Logging
logger = logging.getLogger(__name__)


class LogTimesMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.


    def __call__(self, request):
        t1 = datetime.now()
        #  pdb.set_trace()

        response = self.get_response(request)

        t2 = datetime.now()
        seconds_elapsed = (t2 - t1).total_seconds()

        logger.info("Called at: ", request.get_raw_uri()) # or path, or get_full_path() for just /polls/
        logger.info("Seconds for call was: ", seconds_elapsed)
        logger.info("Headers returned were: ", response._headers)

        #  pdb.set_trace()

        return response


    # in initial testing view_args and view_kwargs were both empty data structures 
    # (Pdb) p view_args
    # ()
    # (Pdb) p view_kwargs
    # {}
    def process_view(self, request, view_func, view_args, view_kwargs):
        logger.info("Process View Callback - Running: ", view_func.__code__.co_filename, " function: ", view_func.__code__.co_name)

        return None

    def process_exception(self, request, exception): # (only if the view raised an exception)
        logger.info("Raised an exception!")
        return None

    def process_template_response(self, request, response): # (only for template responses)
        logger.info("Going to render a template: ", response.template_name)
        return response


