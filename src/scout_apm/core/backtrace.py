# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import traceback

if sys.version_info >= (3, 5):

    def capture():
        return [
            {"file": frame.filename, "line": frame.lineno, "function": frame.name}
            for frame in reversed(traceback.extract_stack()[:-1])
        ]


else:

    def capture():
        return [
            {"file": frame[0], "line": frame[1], "function": frame[3]}
            for frame in reversed(traceback.extract_stack()[:-1])
        ]
