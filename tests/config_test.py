import scout_apm


def test_default_socket():
    conf = scout_apm.config.config.ScoutConfig()
    assert('/tmp/scout_core_agent' == conf.value('socket_path'))
