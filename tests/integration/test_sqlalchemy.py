from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from sqlalchemy import create_engine

from scout_apm.sqlalchemy import instrument_sqlalchemy

try:
    from unittest.mock import patch
except ImportError:  # Python 2.7
    from mock import patch


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


def test_hello():
    with conn_with_scout() as conn:
        result = conn.execute("SELECT 'Hello World!'")
        assert list(result) == [("Hello World!",)]


# Monkey patch should_capture_backtrace in order to keep the test fast.
@patch(
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
