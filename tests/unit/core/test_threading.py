# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import threading

import pytest

from scout_apm.core.threading import SingletonThread


class ExampleThread(SingletonThread):
    _instance_lock = threading.Lock()
    _stop_event = threading.Event()

    @classmethod
    def _on_stop(cls):
        cls._on_stop_called = True

    def run(self):
        while not self._stop_event.wait(timeout=1):
            pass


@pytest.fixture(autouse=True)
def ensure_test_thread_stopped():
    try:
        yield
    finally:
        ExampleThread.ensure_stopped()


def test_ensure_started():
    ExampleThread.ensure_started()

    assert isinstance(ExampleThread._instance, ExampleThread)


def test_ensure_started_twice_idempotent():
    ExampleThread.ensure_started()
    instance_1 = ExampleThread._instance
    ExampleThread.ensure_started()
    instance_2 = ExampleThread._instance

    assert isinstance(instance_1, ExampleThread)
    assert isinstance(instance_2, ExampleThread)
    assert instance_1 is instance_2


def test_ensure_started_whilst_holding_lock():
    ExampleThread.ensure_started()
    instance_1 = ExampleThread._instance
    with ExampleThread._instance_lock:
        # Imitate another thread in the process of finishing starting -
        # ensure_started() should still return due to its early check
        ExampleThread.ensure_started()
        instance_2 = ExampleThread._instance

    assert instance_1 is instance_2


def test_restart_makes_new_instance():
    ExampleThread.ensure_started()
    instance_1 = ExampleThread._instance
    ExampleThread.ensure_stopped()
    ExampleThread.ensure_started()
    instance_2 = ExampleThread._instance

    assert instance_1 is not instance_2


def test_ensure_stopped():
    ExampleThread.ensure_stopped()
    assert ExampleThread._instance is None
    assert not ExampleThread._stop_event.is_set()


def test_ensure_stopped_calls_on_stop():
    ExampleThread._on_stop_called = False
    ExampleThread.ensure_started()
    ExampleThread.ensure_stopped()

    assert ExampleThread._on_stop_called


def test_ensure_stopped_whilst_holding_lock():
    with ExampleThread._instance_lock:
        # Imitate another thread in the process of finishign stopping -
        # ensure_stopped should still return due to its early check
        ExampleThread.ensure_stopped()
