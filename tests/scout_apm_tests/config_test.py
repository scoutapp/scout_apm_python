import scout_apm
import os
import re


def test_defaults():
    conf = scout_apm.core.config.ScoutConfig()
    m = re.match(r'/tmp/scout_apm_core/scout_apm_core-latest-(x86_64|i686|unknown)-(unknown-linux-gnu|apple-darwin|unknown)/core-agent\.sock',
                 conf.value('socket_path'))
    assert(m is not None)


def test_env():
    conf = scout_apm.core.config.ScoutConfig()
    os.environ['SCOUT_SOCKET_PATH'] = '/set/in/env'
    assert('/set/in/env' == conf.value('socket_path'))
    del os.environ['SCOUT_SOCKET_PATH']


def test_python():
    scout_apm.core.config.ScoutConfig.set(socket_path='/set/via/function')
    conf = scout_apm.core.config.ScoutConfig()
    assert('/set/via/function' == conf.value('socket_path'))


def test_none():
    conf = scout_apm.core.config.ScoutConfig()
    assert(conf.value('unknown value') is None)


def test_env_outranks_python():
    os.environ['SCOUT_SOCKET_PATH'] = '/set/in/env'
    scout_apm.core.config.ScoutConfig.set(socket_path='/set/via/function')

    conf = scout_apm.core.config.ScoutConfig()
    assert('/set/in/env' == conf.value('socket_path'))

    del os.environ['SCOUT_SOCKET_PATH']

