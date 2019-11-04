# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import django
import wrapt
from django.db import connections
from django.db.backends.signals import connection_created

from scout_apm.core.tracked_request import TrackedRequest

try:
    from django.db.backends.utils import CursorWrapper
except ImportError:
    # Backwards compatibility for Django <1.9
    from django.db.backends.util import CursorWrapper

logger = logging.getLogger(__name__)


def db_execute_hook(execute, sql, params, many, context):
    """
    Database instrumentation hook for Django 2.0+
    https://docs.djangoproject.com/en/2.0/topics/db/instrumentation/
    """
    if many:
        operation = "SQL/Many"
    else:
        operation = "SQL/Query"

    if sql is not None:
        tracked_request = TrackedRequest.instance()
        span = tracked_request.start_span(operation=operation)
        span.tag("db.statement", sql)

    try:
        return execute(sql, params, many, context)
    finally:
        if sql is not None:
            tracked_request.stop_span()
            tracked_request.callset.update(sql, 1, span.duration())
            if tracked_request.callset.should_capture_backtrace(sql):
                span.capture_backtrace()


def install_db_execute_hook(connection, **kwargs):
    """
    Install db_execute_hook on the given database connection.

    Rather than use the documented API of the `execute_wrapper()` context
    manager, directly insert the hook. This is done because:
    1. Deleting the context manager closes it, so it's not possible to enter
       it here and not exit it, unless we store it forever in some variable
    2. We want to be the first hook, so we can capture every query (although
       potentially later hooks will change the SQL)
    3. We want to be idempotent and only install the hook once
    """
    if db_execute_hook not in connection.execute_wrappers:
        connection.execute_wrappers.insert(0, db_execute_hook)


@wrapt.decorator
def execute_wrapper(wrapped, instance, args, kwargs):
    """
    CursorWrapper.execute() wrapper for Django < 2.0
    """
    try:
        sql = _extract_sql(*args, **kwargs)
    except TypeError:
        sql = None

    if sql is not None:
        tracked_request = TrackedRequest.instance()
        span = tracked_request.start_span(operation="SQL/Query")
        span.tag("db.statement", sql)

    try:
        return wrapped(*args, **kwargs)
    finally:
        if sql is not None:
            tracked_request.stop_span()
            tracked_request.callset.update(sql, 1, span.duration())
            if tracked_request.callset.should_capture_backtrace(sql):
                span.capture_backtrace()


@wrapt.decorator
def executemany_wrapper(wrapped, instance, args, kwargs):
    """
    CursorWrapper.executemany() wrapper for Django < 2.0
    """
    try:
        sql = _extract_sql(*args, **kwargs)
    except TypeError:
        sql = None

    if sql is not None:
        tracked_request = TrackedRequest.instance()
        span = tracked_request.start_span(operation="SQL/Many")
        span.tag("db.statement", sql)

    try:
        return wrapped(*args, **kwargs)
    finally:
        if sql is not None:
            tracked_request.stop_span()
            tracked_request.callset.update(sql, 1, span.duration())
            if tracked_request.callset.should_capture_backtrace(sql):
                span.capture_backtrace()


def _extract_sql(sql, *args, **kwargs):
    return sql


def install_sql_instrumentation():
    if getattr(install_sql_instrumentation, "installed", False):
        return
    install_sql_instrumentation.installed = True

    if django.VERSION >= (2, 0):
        for connection in connections.all():
            install_db_execute_hook(connection=connection)
        connection_created.connect(install_db_execute_hook)
        logger.debug("Installed DB connection created signal handler")
    else:

        CursorWrapper.execute = execute_wrapper(CursorWrapper.execute)
        CursorWrapper.executemany = executemany_wrapper(CursorWrapper.executemany)

        logger.debug("Monkey patched SQL")
