from __future__ import absolute_import, division, print_function, unicode_literals

from sqlalchemy import event

from scout_apm.core.tracked_request import TrackedRequest


def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    tr = TrackedRequest.instance()
    span = tr.start_span(operation="SQL/Query")
    span.tag("db.statement", statement)


def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    tr = TrackedRequest.instance()
    span = tr.current_span()
    if span is not None:
        tr.callset.update(statement, 1, span.duration())
        if tr.callset.should_capture_backtrace(statement):
            span.capture_backtrace()
    tr.stop_span()


def instrument_sqlalchemy(engine):
    if getattr(engine, "_scout_instrumented", False):
        return
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    engine._scout_instrumented = True
