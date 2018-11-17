# Module for helper functions to capture tracebacks

from __future__ import absolute_import, division, print_function, unicode_literals

import traceback


def capture():
    stack = traceback.extract_stack()
    formatted_stack = []
    for frame in stack:
        # Python 2.7 and 3.4 returned tuples
        if type(frame) is tuple:
            filename = frame[0]
            line = frame[1]
            function = frame[3]
        # 3.5+ returned objects
        else:
            filename = frame.filename
            line = frame.lineno
            function = frame.name

        formatted_stack.append({"file": filename, "line": line, "function": function})

    # Python puts the closest stack frames at the end of the traceback. But we
    # want them up front
    formatted_stack.reverse()

    return formatted_stack
