import scout_apm


def test_default_socket():
    conf = scout_apm.config.config.ScoutConfig()
    assert('/tmp/scout_core_agent' == conf.value('core_agent_socket'))
