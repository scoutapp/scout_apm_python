# coding=utf-8

import logging

import pytest

from scout_apm.core.cli.core_agent_manager import main
from tests.compat import mock


@pytest.fixture(autouse=True)
def mock_CoreAgentManager():
    # Always mock out the actual CoreAgentManager class for these tests, to
    # keep them quick
    path = "scout_apm.core.cli.core_agent_manager.CoreAgentManager"
    with mock.patch(path) as mock_obj:
        yield mock_obj


@mock.patch("scout_apm.core.cli.core_agent_manager.logging.basicConfig")
@pytest.mark.parametrize(
    "args, expected_level", [(["-v"], logging.INFO), (["-v", "-v"], logging.DEBUG)]
)
def test_logging_verbose(mock_basicConfig, args, expected_level):
    # Have to use a mock for basicConfig since logging is already configured
    # during tests
    main(args + ["download"])

    mock_basicConfig.assert_called_with(level=expected_level)


@pytest.mark.parametrize("command", ["download", "launch"])
def test_command(mock_CoreAgentManager, command):
    main([command])

    instance = mock_CoreAgentManager.return_value
    method = getattr(instance, command)
    method.assert_called_with()
