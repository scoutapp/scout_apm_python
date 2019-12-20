# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

# The async_ module can only be shipped on Python 3.6+
try:
    from scout_apm.async_.channels import instrument_channels
except ImportError:  # pragma: no cover
    instrument_channels = None


logger = logging.getLogger(__name__)

instrumented = False


def ensure_instrumented():
    global instrumented
    if instrumented:
        return
    instrumented = True

    if instrument_channels is not None:  # pragma: no cover
        instrument_channels()
