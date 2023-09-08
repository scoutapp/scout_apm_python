# coding=utf-8

import logging

from scout_apm.core.samplers.memory import Memory


def test_run(caplog):
    result = Memory().run()
    assert isinstance(result, float) and result > 0.0
    record_tuples = [
        r for r in caplog.record_tuples if r[0] == "scout_apm.core.samplers.memory"
    ]
    assert len(record_tuples) == 1
    _, level, message = record_tuples[0]
    assert level == logging.DEBUG
    assert message.startswith("Process Memory: #")
