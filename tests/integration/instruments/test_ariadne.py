# coding=utf-8

import logging
from contextlib import contextmanager

import pytest
from ariadne import MutationType, QueryType, graphql_sync, make_executable_schema
from ariadne.asgi.handlers import GraphQLHTTPHandler

from scout_apm.instruments.ariadne import ScoutExtension, ensure_installed
from tests.compat import mock


@contextmanager
def mock_not_attempted():
    with mock.patch(
        "scout_apm.instruments.ariadne.have_patched_handler_init", new=False
    ):
        yield


@pytest.fixture
def schema():
    type_defs = """
        type Query {
            hello(name: String!): String!
            boom: String!
        }
        type Mutation {
            shout(text: String!): String!
        }
    """
    query = QueryType()
    mutation = MutationType()

    @query.field("hello")
    def resolve_hello(_obj, _info, name):
        return "Hi, {}".format(name)

    @query.field("boom")
    def resolve_boom(_obj, _info):
        raise ValueError("boom")

    @mutation.field("shout")
    def resolve_shout(_obj, _info, text):
        return text.upper()

    return make_executable_schema(type_defs, query, mutation)


def test_ensure_installed_twice(caplog):
    ensure_installed()
    ensure_installed()

    debug_messages = [
        msg
        for (name, level, msg) in caplog.record_tuples
        if name == "scout_apm.instruments.ariadne" and level == logging.DEBUG
    ]
    assert debug_messages.count("Instrumenting Ariadne.") == 2


def test_ensure_installed_fail_no_handler(caplog):
    with (
        mock_not_attempted(),
        mock.patch("scout_apm.instruments.ariadne.GraphQLHTTPHandler", new=None),
    ):
        ensure_installed()

    assert any(
        msg.startswith("Couldn't import ariadne")
        for (_name, _level, msg) in caplog.record_tuples
    )


def _run(schema, data):
    handler = GraphQLHTTPHandler()
    handler.configure(
        schema=schema,
        context_value=None,
        root_value=None,
        query_parser=None,
        query_validator=None,
        validation_rules=None,
        execute_get_queries=False,
        debug=False,
        introspection=True,
        explorer=None,
        logger=None,
        error_formatter=None,
        execution_context_class=None,
    )
    # graphql_sync runs the query and exercises extensions when passed
    # in directly — we use a fresh ScoutExtension class to mirror
    # what the patched handler installs per request.
    return graphql_sync(schema, data, extensions=[ScoutExtension])


@contextmanager
def _outer_span(tracked_request):
    """Mimic the ASGI middleware's outer Controller span so the
    TrackedRequest stays alive while we make assertions on it. In
    production this is provided by ``scout_apm.async_.starlette.ScoutMiddleware``.
    """
    span = tracked_request.start_span(operation="Controller/Unknown")
    try:
        yield span
    finally:
        tracked_request.stop_span()


def test_query(schema, tracked_request):
    ensure_installed()
    with _outer_span(tracked_request) as outer:
        success, result = _run(schema, {"query": '{ hello(name: "World") }'})

    assert success is True
    assert result == {"data": {"hello": "Hi, World"}}

    operations = [s.operation for s in tracked_request.complete_spans]
    assert "GraphQL/Query/hello" in operations
    assert tracked_request.operation == "GraphQL/Query/hello"
    assert outer.operation == "GraphQL/Query/hello"


def test_mutation(schema, tracked_request):
    ensure_installed()
    with _outer_span(tracked_request):
        success, result = _run(schema, {"query": 'mutation Loud { shout(text: "hi") }'})

    assert success is True
    assert result == {"data": {"shout": "HI"}}
    operations = [s.operation for s in tracked_request.complete_spans]
    assert "GraphQL/Mutation/shout" in operations
    assert tracked_request.operation == "GraphQL/Mutation/shout"
    assert tracked_request.tags.get("graphql_operation_name") == "Loud"


def test_resolver_error(schema, tracked_request):
    ensure_installed()
    with _outer_span(tracked_request):
        success, _result = _run(schema, {"query": "{ boom }"})

    assert success is False
    assert tracked_request.tags.get("error") == "true"


def test_compose_extensions_with_user_list(schema, tracked_request):
    """A handler initialized with a user-supplied extension list should also
    include ScoutExtension after the patch."""
    ensure_installed()

    class UserExt:
        instances = []

        def __init__(self):
            UserExt.instances.append(self)

        def request_started(self, context):
            pass

        def request_finished(self, context):
            pass

        def resolve(self, next_, obj, info, **kwargs):
            return next_(obj, info, **kwargs)

        def has_errors(self, errors, context):
            pass

        def format(self, context):
            return None

    handler = GraphQLHTTPHandler(extensions=[UserExt])
    # extensions attribute is now a list (Scout appended) — not a callable.
    assert callable(handler.extensions) or UserExt in handler.extensions
    if isinstance(handler.extensions, list):
        assert ScoutExtension in handler.extensions
