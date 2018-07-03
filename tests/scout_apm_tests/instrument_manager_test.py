from scout_apm.core.instrument_manager import InstrumentManager


# Fake instrument - note, this uses a module level global var to track if it's
# been installed. Reset it after your test to reuse.
installed_fake_instrument = False
def install():
    global installed_fake_instrument
    installed_fake_instrument = True
    return True


# Fake instrument - note, this uses a module level global var to track if it's
# been installed. Reset it after your test to reuse.
klassy_instrument_pos_arg = False
klassy_instrument_kwarg = False
class KlassyInstrument():
    def __init__(self, pos_arg, kwarg=None):
        self.pos_arg = pos_arg
        self.kwarg = kwarg

    def install(self):
        global klassy_instrument_pos_arg
        global klassy_instrument_kwarg

        klassy_instrument_pos_arg = self.pos_arg
        klassy_instrument_kwarg = self.kwarg
        return True

# Fake instrument - note, this uses a module level global var to track if it's
# been installed. Reset it after your test to reuse.
class ExceptionalInstrument():
    def __init__(self):
        pass

    def install(self):
        raise Exception("foo")


def test_loads_instrument():
    global installed_fake_instrument

    assert(not installed_fake_instrument)
    result = InstrumentManager().install('scout_apm_tests.instrument_manager_test')
    assert(installed_fake_instrument)
    assert(result)

    installed_fake_instrument = False


def test_loads_class_instrument():
    global klassy_instrument_pos_arg
    global klassy_instrument_kwarg

    assert(not klassy_instrument_pos_arg)
    assert(not klassy_instrument_kwarg)

    result = InstrumentManager().install('scout_apm_tests.instrument_manager_test', 'KlassyInstrument', 'pos arg', kwarg='kwarg')

    assert(klassy_instrument_pos_arg == 'pos arg')
    assert(klassy_instrument_kwarg == 'kwarg')
    assert(result)

    klassy_instrument_pos_arg = False
    klassy_instrument_kwarg = False


def test_handles_exception():
    result = InstrumentManager().install('scout_apm_tests.instrument_manager_test', 'ExceptionalInstrument')
    assert(not result)

