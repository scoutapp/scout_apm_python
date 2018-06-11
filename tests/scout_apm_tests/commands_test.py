import scout_apm.core.commands
from scout_apm.core.tracked_request import TrackedRequest

def test_stop_span_defaults_timestamp_to_invalid_date():
    command = scout_apm.core.commands.StopSpan(request_id="req_id", span_id="span_id")
    assert(command.timestamp == scout_apm.core.commands.INVALID_DATE)


def test_finish_request_defaults_timestamp_to_invalid_date():
    command = scout_apm.core.commands.FinishRequest(request_id="req_id")
    assert(command.timestamp == scout_apm.core.commands.INVALID_DATE)


def test_from_tracked_request_bails_on_unfinished_span():
    tr = TrackedRequest()
    tr.start_span("foo")
    batch = scout_apm.core.commands.BatchCommand.from_tracked_request(tr)
    assert(batch is None)


def test_from_tracked_request_bails_on_unfinished_request():
    tr = TrackedRequest()
    batch = scout_apm.core.commands.BatchCommand.from_tracked_request(tr)
    assert(batch is None)


def test_from_tracked_request_creates_batch_command():
    tr = TrackedRequest()
    tr.start_span("foo")
    tr.stop_span()

    batch = scout_apm.core.commands.BatchCommand.from_tracked_request(tr)
    assert(len(batch.commands) == 4)
