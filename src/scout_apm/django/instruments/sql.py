from __future__ import absolute_import
import logging

from scout_apm.core.monkey import monkeypatch_method
from scout_apm.core.tracked_request import TrackedRequest

try:
    from django.db.backends.base.base import BaseDatabaseWrapper
except ImportError:
    # Backwards compatibility for Django <1.8
    from django.db.backends import BaseDatabaseWrapper

try:
    from django.db.backends.utils import CursorWrapper
except ImportError:
    # Backwards compatibility for Django <1.9
    from django.db.backends.util import CursorWrapper

logger = logging.getLogger(__name__)


class _DetailedTracingCursorWrapper(CursorWrapper):
    def execute(self, sql, params=None):
        tr = TrackedRequest.instance()
        span = tr.start_span(operation='SQL/Query')
        span.tag('db.statement', sql)

        try:
            return self.cursor.execute(sql, params)
        finally:
            tr.stop_span()
            tr.callset.update(sql, 1, span.duration())
            if tr.callset.should_capture_backtrace(sql) is True:
                span.capture_backtrace()

    def executemany(self, sql, param_list):
        tr = TrackedRequest.instance()
        span = tr.start_span(operation='SQL/Many')
        span.tag('db.statement', sql)

        try:
            return self.cursor.executemany(sql, param_list)
        finally:
            tr.stop_span()
            tr.callset.update(sql, 1, span.duration())
            if tr.callset.should_capture_backtrace(sql) is True:
                span.capture_backtrace()


# pylint: disable=too-few-public-methods
class SQLInstrument:

    # The linter thinks the methods we monkeypatch are not used
    # pylint: disable=W0612
    # pylint: disable=no-method-argument
    @staticmethod
    def install():
        """
        Installs ScoutApm SQL Instrumentation by monkeypatching the `cursor`
        method of BaseDatabaseWrapper, to return a wrapper that instruments any
        calls going through it.
        """
        @monkeypatch_method(BaseDatabaseWrapper)
        def cursor(original, self, *args, **kwargs):
            result = original(*args, **kwargs)
            return _DetailedTracingCursorWrapper(result, self)

        logger.debug('Monkey patched SQL')
