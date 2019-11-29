# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from sqlalchemy import event

from scout_apm.core.tracked_request import TrackedRequest


def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if executemany:
        operation = "SQL/Many"
    else:
        operation = "SQL/Query"
    tracked_request = TrackedRequest.instance()
    span = tracked_request.start_span(operation=operation)
    span.tag("db.statement", statement)


def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    tracked_request = TrackedRequest.instance()
    span = tracked_request.current_span()
    if span is not None:
        callset_item = tracked_request.callset[statement]
        callset_item.update(span.duration())
        if callset_item.should_capture_backtrace():
            span.capture_backtrace()
    tracked_request.stop_span()


def instrument_sqlalchemy(engine):
    if getattr(engine, "_scout_instrumented", False):
        return
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    engine._scout_instrumented = True
