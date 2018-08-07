from scout_apm import objtrace


def test_enables_and_disabled():
    objtrace.enable()
    objtrace.get_counts()
    objtrace.disable()


def test_allocation_counts():
    l = []
    objtrace.enable()
    for _ in range(100):
        l.append([1])
    c = objtrace.get_counts()
    assert((99, 0, 0, 2) == c)
