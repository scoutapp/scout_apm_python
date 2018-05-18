# Module for helper functions to capture tracebacks

import traceback


def capture():
    stack = traceback.extract_stack()
    formatted_stack = []
    for frame in stack:
        formatted_stack.append({
            'file': frame.filename,
            'line': frame.lineno,
            'function': frame.name,
        })

    # Python puts the closest stack frames at the end of the traceback. But we
    # want them up front
    formatted_stack.reverse()

    return formatted_stack

