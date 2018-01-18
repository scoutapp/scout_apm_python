"""
DOCS!
"""
from __future__ import absolute_import

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

from datetime import datetime
from scout_apm.monkey import monkeypatch_method
from scout_apm.tracked_request import TrackedRequest

"""
DOCS!
"""
class _DetailedTracingCursorWrapper(CursorWrapper):
    def execute(self, sql, params=()):
        tr = TrackedRequest.instance()
        span = tr.start_span(operation="SQL/query")
        span.note("query", sql)

        try:
            return self.cursor.execute(sql, params)
        finally:
            tr.stop_span()
            print(span.dump())

    def executemany(self, sql, param_list):
        span = TrackedRequest.instance().start_span(operation="SQL/many")
        span.note("query", sql)

        try:
            return self.cursor.executemany(sql, param_list)
        finally:
            TrackedRequest.instance().stop_span()
            print(span.dump())

# pylint: disable=too-few-public-methods
class SQLInstrument:

    # The linter thinks the methods we monkeypatch are not used
    # pylint: disable=W0612
    # pylint: disable=no-method-argument
    @staticmethod
    def install():
        """
        DOCS!
        """
        @monkeypatch_method(BaseDatabaseWrapper)
        def cursor(original, self, *args, **kwargs):
            """
            DOCS!
            """
            result = original(*args, **kwargs)
            return _DetailedTracingCursorWrapper(result, self)

        print('Monkey patched SQL')
