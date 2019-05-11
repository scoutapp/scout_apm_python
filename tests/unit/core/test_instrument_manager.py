# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core.config import ScoutConfig
from scout_apm.core.context import AgentContext
from scout_apm.core.instrument_manager import InstrumentManager
from tests.compat import mock

# Default instrument name
default_instrument_installed = False


class Instrument(object):
    def install(self):
        global default_instrument_installed

        default_instrument_installed = True
        return True


# Fake instrument - note, this uses a module level global var to track if it's
# been installed. Reset it after your test to reuse.
klassy_instrument_pos_arg = False
klassy_instrument_kwarg = False


class KlassyInstrument(object):
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
class ExceptionalInstrument(object):
    def __init__(self):
        pass

    def install(self):
        raise Exception("foo")


def test_loads_default_instrument():
    global default_instrument_installed
    assert not default_instrument_installed

    try:
        assert InstrumentManager().install(__name__)
        assert default_instrument_installed
    finally:
        default_instrument_installed = False


def test_loads_class_instrument():
    global klassy_instrument_pos_arg
    global klassy_instrument_kwarg
    assert not klassy_instrument_pos_arg
    assert not klassy_instrument_kwarg

    try:
        assert InstrumentManager().install(
            __name__, "KlassyInstrument", "pos arg", kwarg="kwarg"
        )
        assert klassy_instrument_pos_arg == "pos arg"
        assert klassy_instrument_kwarg == "kwarg"
    finally:
        klassy_instrument_pos_arg = False
        klassy_instrument_kwarg = False


def test_handles_exception():
    assert not InstrumentManager().install(__name__, "ExceptionalInstrument")


def test_install_all_installs_only_enabled_instruments():
    # Disable all instruments except the last one.
    ScoutConfig.set(disabled_instruments=InstrumentManager.DEFAULT_INSTRUMENTS[:-1])
    AgentContext.build()

    try:
        with mock.patch(
            "scout_apm.core.instrument_manager.InstrumentManager.install"
        ) as install:
            # Only the last instrument is installed.
            InstrumentManager().install_all()
            install.assert_called_once_with(
                "{}.{}".format(
                    InstrumentManager.INSTRUMENT_NAMESPACE,
                    InstrumentManager.DEFAULT_INSTRUMENTS[-1],
                )
            )
    finally:
        ScoutConfig.reset_all()
