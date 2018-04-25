import scout_apm


def test_traceback():
    traceback = scout_apm.core.traceback.capture()
    for frame in traceback:
        keys = list(frame.keys())
        keys.sort()
        assert(keys == ['file', 'function', 'line'])

