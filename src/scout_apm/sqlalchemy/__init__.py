from scout_apm.core.tracked_request import TrackedRequest

from sqlalchemy import event

def instrument_sqlalchemy(engine):
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        tr = TrackedRequest.instance()
        span = tr.start_span(operation='SQL/Query')
        span.tag('db.statement', statement)

    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        tr = TrackedRequest.instance()
        tr.stop_span()

    if getattr(engine, "_scout_instrumented", False) != True:
        event.listen(engine, 'before_cursor_execute', before_cursor_execute)
        event.listen(engine, 'after_cursor_execute', after_cursor_execute)
        setattr(engine, "_scout_instrumented", True)
