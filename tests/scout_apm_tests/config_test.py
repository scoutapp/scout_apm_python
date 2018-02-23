import scout_apm
import os
import re


def test_defaults():
    conf = scout_apm.config.config.ScoutConfig()
    m = re.match(r'/tmp/scout_apm_core/scout_apm_core-latest-(linux|darwin|unknown)-(x86_64|i686|unknown)/core-agent\.sock',
                 conf.value('socket_path'))
    assert(m is not None)


def test_env():
    conf = scout_apm.config.config.ScoutConfig()
    os.environ['SCOUT_SOCKET_PATH'] = '/set/in/test'
    assert('/set/in/test' == conf.value('socket_path'))


def test_none():
    conf = scout_apm.config.config.ScoutConfig()
    assert(conf.value('unknown value') is None)
