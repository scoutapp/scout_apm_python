# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import traceback

# Maximum non-Scout frames to target retrieving
LIMIT = 50
# How many upper frames from inside Scout to ignore
IGNORED = 1


if sys.version_info >= (3, 5):

    def capture():
        return [
            {"file": frame.filename, "line": frame.lineno, "function": frame.name}
            for frame in reversed(
                traceback.extract_stack(limit=LIMIT + IGNORED)[:-IGNORED]
            )
        ]


else:

    def capture():
        return [
            {"file": frame[0], "line": frame[1], "function": frame[3]}
            for frame in reversed(
                traceback.extract_stack(limit=LIMIT + IGNORED)[:-IGNORED]
            )
        ]
