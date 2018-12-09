from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core.n_plus_one_call_set import NPlusOneCallSet, NPlusOneCallSetItem

SQL = "SELECT * from test"
CALL_COUNT_THRESHOLD = NPlusOneCallSetItem.CALL_COUNT_THRESHOLD
DURATION_THRESHOLD = NPlusOneCallSetItem.DURATION_THRESHOLD


def test_call_set_find_for_creates_new_item():
    callset = NPlusOneCallSet()
    assert len(callset.items) == 0
    item = callset.find_for(SQL)
    assert len(callset.items) == 1
    assert item.sql_string == SQL


def test_call_set_find_for_returns_existing_item():
    callset = NPlusOneCallSet()
    item1 = callset.find_for(SQL)
    item2 = callset.find_for(SQL)
    assert len(callset.items) == 1
    assert item1 is item2


def test_call_set_update_sets_call_count_and_duration():
    callset = NPlusOneCallSet()
    callset.update(SQL, 3, 0.11)
    item = callset.find_for(SQL)
    assert item.call_count == 3
    assert item.call_duration == 0.11


def test_call_set_update_increments_call_count_and_duration():
    callset = NPlusOneCallSet()
    callset.update(SQL, 3, 0.11)
    callset.update(SQL, 2, 0.07)
    item = callset.find_for(SQL)
    assert item.call_count == 5
    assert item.call_duration == 0.18


def test_call_set_should_capture_backtrace():
    callset = NPlusOneCallSet()
    callset.update(SQL, CALL_COUNT_THRESHOLD // 2, DURATION_THRESHOLD / 2)
    assert not callset.should_capture_backtrace(SQL)
    callset.update(SQL, CALL_COUNT_THRESHOLD, DURATION_THRESHOLD)
    assert callset.should_capture_backtrace(SQL)


def test_call_set_should_capture_backtrace_only_once():
    callset = NPlusOneCallSet()
    callset.update(SQL, CALL_COUNT_THRESHOLD, DURATION_THRESHOLD)
    assert callset.should_capture_backtrace(SQL)
    assert not callset.should_capture_backtrace(SQL)
    callset.update(SQL, CALL_COUNT_THRESHOLD // 2, DURATION_THRESHOLD / 2)
    assert not callset.should_capture_backtrace(SQL)


def test_call_set_update_no_longer_increments_call_count_and_duration_after_capture():
    callset = NPlusOneCallSet()
    callset.update(SQL, CALL_COUNT_THRESHOLD, DURATION_THRESHOLD)
    callset.should_capture_backtrace(SQL)
    callset.update(SQL, CALL_COUNT_THRESHOLD // 2, DURATION_THRESHOLD // 2)
    item = callset.find_for(SQL)
    assert item.call_count == CALL_COUNT_THRESHOLD
    assert item.call_duration == DURATION_THRESHOLD
