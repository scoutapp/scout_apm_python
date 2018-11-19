from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re

import scout_apm


def test_defaults():
    conf = scout_apm.core.config.ScoutConfig()
    assert re.match(
        r"/tmp/scout_apm_core/scout_apm_core"
        r"-(latest|v\d\.\d.\d(.\d)?)"
        r"-(x86_64|i686|unknown)"
        r"-(unknown-linux-gnu|apple-darwin|unknown)"
        r"/core-agent\.sock",
        conf.value("socket_path"),
    )


def test_env():
    conf = scout_apm.core.config.ScoutConfig()
    os.environ["SCOUT_SOCKET_PATH"] = "/set/in/env"
    assert "/set/in/env" == conf.value("socket_path")
    del os.environ["SCOUT_SOCKET_PATH"]


def test_python():
    scout_apm.core.config.ScoutConfig.set(socket_path="/set/via/function")
    conf = scout_apm.core.config.ScoutConfig()
    assert "/set/via/function" == conf.value("socket_path")
    scout_apm.core.config.ScoutConfig.reset_all()


def test_none():
    conf = scout_apm.core.config.ScoutConfig()
    assert conf.value("unknown value") is None


def test_env_outranks_python():
    os.environ["SCOUT_SOCKET_PATH"] = "/set/in/env"
    scout_apm.core.config.ScoutConfig.set(socket_path="/set/via/function")

    conf = scout_apm.core.config.ScoutConfig()
    assert "/set/in/env" == conf.value("socket_path")

    del os.environ["SCOUT_SOCKET_PATH"]
    scout_apm.core.config.ScoutConfig.reset_all()


def test_socket_path_matches_version():
    scout_apm.core.config.ScoutConfig.set(core_agent_version="v1.1.5")
    conf = scout_apm.core.config.ScoutConfig()
    assert "v1.1.5" in conf.value("socket_path")
