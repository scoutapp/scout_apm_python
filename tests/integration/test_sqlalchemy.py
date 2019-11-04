# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from sqlalchemy import create_engine

from scout_apm.sqlalchemy import instrument_sqlalchemy
from tests.compat import mock


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
        result = conn.execute("SELECT 'Hello World!'")

    assert list(result) == [("Hello World!",)]
    assert len(tracked_request.complete_spans) == 1
    span = tracked_request.complete_spans[0]
    assert span.operation == "SQL/Query"
    assert span.tags["db.statement"] == "SELECT 'Hello World!'"


def test_many_query(tracked_request):
    tracked_request.start_span(operation="parent")
    with conn_with_scout() as conn:
        conn.execute("CREATE TABLE t(i integer)")
        conn.execute("INSERT INTO t(i) VALUES (?)", [1], [2])

    spans = tracked_request.complete_spans
    assert len(spans) == 2
    assert spans[0].operation == "SQL/Query"
    assert spans[0].tags["db.statement"] == "CREATE TABLE t(i integer)"
    assert spans[1].operation == "SQL/Many"
    assert spans[1].tags["db.statement"] == "INSERT INTO t(i) VALUES (?)"


# Monkey patch should_capture_backtrace in order to keep the test fast.
@mock.patch(
    "scout_apm.core.n_plus_one_call_set.NPlusOneCallSetItem.should_capture_backtrace"
)
def test_hello_capture_backtrace(should_capture_backtrace):
    should_capture_backtrace.return_value = True
    with conn_with_scout() as conn:
        result = conn.execute("SELECT 'Hello World!'")
        assert list(result) == [("Hello World!",)]


def test_instrument_engine_is_idempotent():
    engine = create_engine("sqlite:///:memory:")
    instrument_sqlalchemy(engine)
    instrument_sqlalchemy(engine)  # does nothing, doesn't crash
