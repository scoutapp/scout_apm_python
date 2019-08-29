# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime as dt
import logging

from psutil._common import pcputimes

from scout_apm.core.samplers.cpu import Cpu


def test_metric_type():
    assert Cpu().metric_type() == "CPU"


def test_metric_name():
    assert Cpu().metric_name() == "Utilization"


def test_human_name():
    assert Cpu().human_name() == "Process CPU"


def test_run_negative_time_elapsed(caplog):
    caplog.set_level(logging.DEBUG)
    cpu = Cpu()
    cpu.last_run = dt.datetime.utcnow() + dt.timedelta(days=100)

    result = cpu.run()

    assert result is None
    assert len(caplog.record_tuples) == 1
    logger, level, message = caplog.record_tuples[0]
    assert logger == "scout_apm.core.samplers.cpu"
    assert level == logging.DEBUG
    assert message.startswith("Process CPU: Negative time elapsed. now: ")


def test_run_negative_last_cpu_times(caplog):
    caplog.set_level(logging.DEBUG)
    cpu = Cpu()
    cpu.last_cpu_times = pcputimes(
        user=1e12, system=1e12, children_user=0.0, children_system=0.0
    )

    result = cpu.run()

    assert result is None
    assert len(caplog.record_tuples) == 1
    logger, level, message = caplog.record_tuples[0]
    assert logger == "scout_apm.core.samplers.cpu"
    assert level == logging.DEBUG
    assert message.startswith("Process CPU: Negative process time elapsed. utime: ")
    assert message.endswith("This is normal to see when starting a forking web server.")


def test_run_within_zero_seconds(caplog):
    caplog.set_level(logging.DEBUG)
    cpu = Cpu()
    # Force the calculation of normalized_wall_clock_elapsed to 0
    cpu.num_processors = 0

    result = cpu.run()

    assert result == 0
    assert caplog.record_tuples == [
        ("scout_apm.core.samplers.cpu", logging.DEBUG, "Process CPU: 0 [0 CPU(s)]")
    ]


def test_run(caplog):
    caplog.set_level(logging.DEBUG)
    cpu = Cpu()

    result = cpu.run()

    assert isinstance(result, float) and result > 0
    logger, level, message = caplog.record_tuples[0]
    assert logger == "scout_apm.core.samplers.cpu"
    assert level == logging.DEBUG
    assert message.startswith("Process CPU: {}".format(result))
