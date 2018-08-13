import unittest

try:
    from scout_apm.core import objtrace
    HAS_OBJTRACE = True
except ImportError:
    HAS_OBJTRACE = False


if HAS_OBJTRACE:
    class TestObjtrace(unittest.TestCase):
        def setUp(self):
            objtrace.reset_counts()

        def tearDown(self):
            objtrace.reset_counts()

        def test_enables_and_disabled(self):
            objtrace.enable()
            objtrace.get_counts()
            objtrace.disable()

        def test_allocation_counts(self):
            l = []
            objtrace.enable()
            for _ in range(100):
                l.append([1])
            objtrace.disable()
            c = objtrace.get_counts()
            assert(c[0] > 0)

        def test_frees_counts(self):
            objtrace.enable()
            for x in (1, 2, 3):
                y = x
            c = objtrace.get_counts()
            assert(c[3] > 0)

    if __name__ == '__main__':
        unittest.main()
