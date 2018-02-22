import scout_apm
import os


def test_defaults():
    conf = scout_apm.config.config.ScoutConfig()
    assert('/tmp/scout_core_agent' == conf.value('socket_path'))


def test_env():
    conf = scout_apm.config.config.ScoutConfig()
    os.environ['SCOUT_SOCKET_PATH'] = '/set/in/test'
    assert('/set/in/test' == conf.value('socket_path'))


def test_none():
    conf = scout_apm.config.config.ScoutConfig()
    assert(conf.value('unknown value') is None)
