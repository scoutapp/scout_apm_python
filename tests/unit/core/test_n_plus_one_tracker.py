# coding=utf-8

from scout_apm.core.n_plus_one_tracker import NPlusOneTracker


def test_add_single_call_not_captured():
    tracker = NPlusOneTracker()
    should_capture_backtrace = tracker.should_capture_backtrace(
        "SELECT 1", duration=NPlusOneTracker.DURATION_THRESHOLD * 2
    )
    assert not should_capture_backtrace


def test_add_multi_call_not_captured():
    tracker = NPlusOneTracker()
    should_capture_backtrace = tracker.should_capture_backtrace(
        "SELECT 1", duration=0.01, count=NPlusOneTracker.COUNT_THRESHOLD * 2
    )
    assert not should_capture_backtrace


def test_add_single_call_captured():
    tracker = NPlusOneTracker()
    should_capture_backtrace = tracker.should_capture_backtrace(
        "SELECT 1",
        duration=NPlusOneTracker.DURATION_THRESHOLD,
        count=NPlusOneTracker.COUNT_THRESHOLD,
    )
    assert should_capture_backtrace


def test_add_two_calls_second_captured():
    tracker = NPlusOneTracker()
    should_capture_backtrace1 = tracker.should_capture_backtrace(
        "SELECT 1",
        duration=NPlusOneTracker.DURATION_THRESHOLD,
        count=NPlusOneTracker.COUNT_THRESHOLD - 1,
    )
    assert not should_capture_backtrace1
    should_capture_backtrace2 = tracker.should_capture_backtrace(
        "SELECT 1", duration=0.01, count=1
    )
    assert should_capture_backtrace2


def test_add_two_calls_not_recaptured():
    tracker = NPlusOneTracker()
    should_capture_backtrace1 = tracker.should_capture_backtrace(
        "SELECT 1",
        duration=NPlusOneTracker.DURATION_THRESHOLD,
        count=NPlusOneTracker.COUNT_THRESHOLD,
    )
    assert should_capture_backtrace1
    should_capture_backtrace2 = tracker.should_capture_backtrace(
        "SELECT 1",
        duration=NPlusOneTracker.DURATION_THRESHOLD,
        count=NPlusOneTracker.COUNT_THRESHOLD,
    )
    assert not should_capture_backtrace2
