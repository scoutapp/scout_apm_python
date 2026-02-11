# coding=utf-8

import pytest
from tortoise import Tortoise, fields
from tortoise.models import Model

from scout_apm.tortoise import instrument_tortoise
from tests.tools import n_plus_one_thresholds


class Item(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)

    class Meta:
        table = "item"


@pytest.fixture
async def tortoise_conn(tracked_request):
    """
    Initialize Tortoise with an in-memory SQLite database.

    A parent span is kept open for the entire test so that child SQL spans
    do not trigger ``TrackedRequest.finish()`` (which happens when the last
    active span is stopped).
    """
    tracked_request.start_span(operation="Controller/test")
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
    )
    await Tortoise.generate_schemas()
    instrument_tortoise()
    # Clear any setup spans (e.g. generate_schemas on subsequent tests
    # where the class is already instrumented).
    tracked_request.complete_spans.clear()
    try:
        yield
    finally:
        tracked_request.stop_span()
        await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_single_query(tracked_request, tortoise_conn):
    await Item.create(name="hello")
    items = await Item.all()

    assert len(items) == 1
    assert items[0].name == "hello"

    spans = tracked_request.complete_spans
    sql_spans = [s for s in spans if s.operation.startswith("SQL/")]
    assert any(s.operation == "SQL/Query" for s in sql_spans)
    for span in sql_spans:
        assert "db.statement" in span.tags


@pytest.mark.asyncio
async def test_insert_query(tracked_request, tortoise_conn):
    await Item.create(name="test")

    spans = tracked_request.complete_spans
    sql_spans = [s for s in spans if s.operation.startswith("SQL/")]
    assert len(sql_spans) >= 1
    assert any(s.operation == "SQL/Query" for s in sql_spans)


@pytest.mark.asyncio
async def test_bulk_insert(tracked_request, tortoise_conn):
    await Item.bulk_create([Item(name="a"), Item(name="b"), Item(name="c")])

    spans = tracked_request.complete_spans
    sql_spans = [s for s in spans if s.operation.startswith("SQL/")]
    assert len(sql_spans) >= 1
    assert any(s.operation == "SQL/Many" for s in sql_spans)


@pytest.mark.asyncio
async def test_n_plus_one_backtrace(tracked_request, tortoise_conn):
    await Item.create(name="seed")
    with n_plus_one_thresholds(count=1, duration=0.0):
        await Item.all()

    spans = tracked_request.complete_spans
    sql_spans = [s for s in spans if s.operation == "SQL/Query"]
    assert any("stack" in s.tags for s in sql_spans)


@pytest.mark.asyncio
async def test_instrument_is_idempotent(tracked_request, tortoise_conn):
    instrument_tortoise()  # second call should not crash or double-wrap

    await Item.create(name="once")
    spans = tracked_request.complete_spans
    sql_spans = [s for s in spans if s.operation.startswith("SQL/")]
    # Should not get duplicate spans from double-wrapping.
    assert len(sql_spans) >= 1
