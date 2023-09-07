# coding=utf-8

import datetime as dt
import logging

from psutil._common import pcputimes

from scout_apm.core.samplers.cpu import Cpu
from tests.compat import mock


def test_run_negative_time_elapsed(caplog):
    cpu = Cpu()
    cpu.last_run = dt.datetime.utcnow() + dt.timedelta(days=100)

    result = cpu.run()

    assert result is None
    record_tuples = [
        r for r in caplog.record_tuples if r[0] == "scout_apm.core.samplers.cpu"
    ]
    assert len(record_tuples) == 1
    _, level, message = record_tuples[0]
    assert level == logging.DEBUG
    assert message.startswith("Process CPU: Negative time elapsed. now: ")


def test_run_negative_last_cpu_times(caplog):
    cpu = Cpu()
    cpu.last_cpu_times = pcputimes(
        user=1e12, system=1e12, children_user=0.0, children_system=0.0
    )

    result = cpu.run()

    assert result is None
    record_tuples = [
        r for r in caplog.record_tuples if r[0] == "scout_apm.core.samplers.cpu"
    ]
    assert len(record_tuples) == 1
    _, level, message = record_tuples[0]
    assert level == logging.DEBUG
    assert message.startswith("Process CPU: Negative process time elapsed. utime: ")
    assert message.endswith("This is normal to see when starting a forking web server.")


def test_run_within_zero_seconds(caplog):
    cpu = Cpu()
    # Force the calculation of normalized_wall_clock_elapsed to 0
    cpu.num_processors = 0

    result = cpu.run()

    assert result == 0
    record_tuples = [
        r for r in caplog.record_tuples if r[0] == "scout_apm.core.samplers.cpu"
    ]
    assert record_tuples == [
        ("scout_apm.core.samplers.cpu", logging.DEBUG, "Process CPU: 0 [0 CPU(s)]")
    ]


def test_run(caplog):
    cpu = Cpu()

    result = cpu.run()

    assert isinstance(result, float) and result >= 0.0
    record_tuples = [
        r for r in caplog.record_tuples if r[0] == "scout_apm.core.samplers.cpu"
    ]
    assert len(record_tuples) == 1
    _, level, message = record_tuples[0]
    assert level == logging.DEBUG
    assert message.startswith("Process CPU: {}".format(result))


def test_run_undetermined_cpus(caplog):
    with mock.patch("psutil.cpu_count", return_value=None):
        cpu = Cpu()

    result = cpu.run()

    assert cpu.num_processors == 1
    assert isinstance(result, float) and result >= 0.0
    record_tuples = [
        r for r in caplog.record_tuples if r[0] == "scout_apm.core.samplers.cpu"
    ]
    assert len(record_tuples) == 2
    assert record_tuples[0] == (
        "scout_apm.core.samplers.cpu",
        logging.DEBUG,
        "Could not determine CPU count - assuming there is one.",
    )
    _, level, message = record_tuples[1]
    assert level == logging.DEBUG
    assert message.startswith("Process CPU: {}".format(result))
