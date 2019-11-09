# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from scout_apm.instruments import ensure_all_installed
from scout_apm.core.config import scout_config


def test_install_all():
    ensure_all_installed()  # no crash


def test_ensure_all_installed_one_disabled(caplog):
    scout_config.set(disabled_instruments=["jinja2"])

    try:
        ensure_all_installed()
    finally:
        scout_config.reset_all()

    instruments_record_tuples = [
        t for t in caplog.record_tuples if t[0] == "scout_apm.instruments"
    ]
    assert len(instruments_record_tuples) == 1
    assert instruments_record_tuples[0] == (
        "scout_apm.instruments",
        logging.INFO,
        "jinja2 instrument is disabled. Skipping.",
    )
