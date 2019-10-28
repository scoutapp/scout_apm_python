# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from scout_apm.core import objtrace

skip_if_objtrace_not_extension = pytest.mark.skipif(
    not objtrace.is_extension, reason="Requires objtrace C extension"
)
skip_if_objtrace_is_extension = pytest.mark.skipif(
    not objtrace.is_extension, reason="Requires no objtrace C extension"
)
