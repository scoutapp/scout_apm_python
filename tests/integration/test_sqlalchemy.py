# coding=utf-8

from contextlib import contextmanager

from sqlalchemy import create_engine, text

from scout_apm.sqlalchemy import instrument_sqlalchemy
from tests.tools import n_plus_one_thresholds


@contextmanager
def conn_with_scout():
    """
    Create an instrumented SQLAlchemy connection to an in-memory SQLite database.

    """
    engine = create_engine("sqlite:///:memory:")
    instrument_sqlalchemy(engine)
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def test_single_query(tracked_request):
    with conn_with_scout() as conn:
        result = conn.execute(text("SELECT 'Hello World!'"))

    assert list(result) == [("Hello World!",)]
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "SQL/Query"
    assert tracked_request.operation == "SQL/Query"
    assert span.tags["db.statement"] == "SELECT 'Hello World!'"


def test_many_query(tracked_request):
    tracked_request.start_span(operation="parent")
    with conn_with_scout() as conn:
        conn.execute(text("CREATE TABLE t(i integer)"))
        values = [1, 2]
        param_list = [{"value": value} for value in values]
        conn.execute(text("INSERT INTO t(i) VALUES (:value)"), param_list)

    spans = tracked_request.complete_spans
    assert len(spans) == 2
    assert spans[0].operation == "SQL/Query"
    assert spans[0].tags["db.statement"] == "CREATE TABLE t(i integer)"
    assert spans[1].operation == "SQL/Many"
    assert spans[1].tags["db.statement"] == "INSERT INTO t(i) VALUES (?)"
    assert tracked_request.operation == "SQL/Many"


def test_execute_capture_backtrace(tracked_request):
    with n_plus_one_thresholds(count=1, duration=0.0), conn_with_scout() as conn:
        result = conn.execute(text("SELECT 'Hello World!'"))

    assert list(result) == [("Hello World!",)]
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "SQL/Query"
    assert span.tags["db.statement"] == "SELECT 'Hello World!'"
    assert tracked_request.operation == "SQL/Query"
    assert "stack" in span.tags


def test_executemany_capture_backtrace(tracked_request):
    tracked_request.start_span(operation="parent")
    with n_plus_one_thresholds(count=2, duration=0.0), conn_with_scout() as conn:
        conn.execute(text("CREATE TABLE t(i integer)"))
        values = [1, 2]
        param_list = [{"value": value} for value in values]
        conn.execute(text("INSERT INTO t(i) VALUES (:value)"), param_list)

    assert len(tracked_request.complete_spans) == 2
    span = tracked_request.complete_spans[1]
    assert span.operation == "SQL/Many"
    assert span.tags["db.statement"] == "INSERT INTO t(i) VALUES (?)"
    assert "stack" in span.tags
    assert tracked_request.operation == "SQL/Many"


def test_instrument_engine_is_idempotent():
    engine = create_engine("sqlite:///:memory:")
    instrument_sqlalchemy(engine)
    instrument_sqlalchemy(engine)  # does nothing, doesn't crash
