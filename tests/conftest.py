# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import sys
import subprocess

import pytest
import wrapt
from webtest import TestApp

from scout_apm.core import socket as scout_apm_core_socket
from scout_apm.core.core_agent_manager import CoreAgentManager
from scout_apm.core.config import SCOUT_PYTHON_VALUES, scout_config
from scout_apm.core.tracked_request import TrackedRequest
from tests.compat import TemporaryDirectory

# Env variables have precedence over Python configs in ScoutConfig.
# Unset all Scout env variables to prevent interference with tests.

for key in os.environ.keys():
    if key.startswith("SCOUT_"):
        del os.environ[key]


# Prevent pytest from trying to collect webtest's TestApp as a test class:
#     PytestWarning: cannot collect test class 'TestApp'
#     because it has a __init__ constructor
# As per https://github.com/pytest-dev/pytest/issues/477

TestApp.__test__ = False


# Override built-in caplog fixture to always be at DEBUG level since we have
# many DEBUG log messages
@pytest.fixture()
def caplog(caplog):
    caplog.set_level(logging.DEBUG)
    yield caplog


# Some files are named to indicate they run on Python 3.6+ only (async
# related) - ignore collecting them on older versions
collect_ignore_glob = []
if sys.version_info < (3, 6):
    collect_ignore_glob.append("*_py36plus.py")


class GlobalStateLeak(Exception):
    """Exception raised when a test leaks global state."""


class ConfigLeak(GlobalStateLeak):
    """Exception raised when a test leaks changes in ScoutConfig."""


class TrackedRequestLeak(GlobalStateLeak):
    """Exception raised when a test leaks an unfinished TrackedRequest."""


@pytest.fixture(autouse=True)
def isolate_global_state():
    """
    Isolate global state in ScoutConfig and TrackedRequest.

    Since scout_apm relies heavily on global variables, it's unfortunately
    easy to leak state changes after a test, which can affect later tests.
    This fixture acts as a safety net. It checks after each test if global
    state was properly reset. If not, it fails the test.

    (An alternative would be to clean up here rather than in each test. The
    original author of this fixture is uncomfortable with such an implicit
    behavior. He prefers enforcing an explicit clean up in tests, requiring
    developers to understand how their test affects global state.)
    """
    try:
        yield
    finally:
        SCOUT_ENV_VARS = {
            key: value for key, value in os.environ.items() if key.startswith("SCOUT_")
        }
        if SCOUT_ENV_VARS:
            raise ConfigLeak("Env config changes: %r" % SCOUT_ENV_VARS)
        if SCOUT_PYTHON_VALUES:
            raise ConfigLeak("Python config changes: %r" % SCOUT_PYTHON_VALUES)

        try:
            request = TrackedRequest._thread_lookup.instance
        except AttributeError:
            pass
        else:
            if request is not None:
                raise TrackedRequestLeak(
                    "Unfinished request: "
                    "active spans = %r, complete spans = %r, tags = %r"
                    % (
                        [(span.operation, span.tags) for span in request.active_spans],
                        [
                            (span.operation, span.tags)
                            for span in request.complete_spans
                        ],
                        request.tags,
                    )
                )


# Create a temporary directory for isolation between test sessions.
# Do it once per test session to avoid downloading the core agent repeatedly.
@pytest.fixture(autouse=True, scope="session")
def core_agent_dir():
    with TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def core_agent_manager(core_agent_dir):
    # Shorten path to socket to prevent core-agent from failing with:
    #   Error opening listener on socket: Custom { kind: InvalidInput,
    #   error: StringError("path must be shorter than SUN_LEN") }
    socket_path = "{}/test.sock".format(core_agent_dir)
    scout_config.set(core_agent_dir=core_agent_dir, socket_path=socket_path)
    core_agent_manager = CoreAgentManager()
    try:
        yield core_agent_manager
    finally:
        assert not is_running(core_agent_manager)
        scout_config.reset_all()


def is_running(core_agent_manager):
    if core_agent_manager.core_agent_bin_path is None:
        return False
    agent_binary = [core_agent_manager.core_agent_bin_path, "probe"]
    socket_path = core_agent_manager.socket_path()
    probe = subprocess.check_output(agent_binary + socket_path)
    if b"Agent found" in probe:
        return True
    if b"Agent Not Running" in probe:
        return False
    raise AssertionError("cannot tell if the core agent is running")


def shutdown(core_agent_manager):
    agent_binary = [core_agent_manager.core_agent_bin_path, "shutdown"]
    socket_path = core_agent_manager.socket_path()
    subprocess.check_call(agent_binary + socket_path)


# Make all timeouts shorter so that tests exercising them run faster.
@pytest.fixture(autouse=True, scope="session")
def short_timeouts():
    scout_apm_core_socket.SECOND = 0.01
    try:
        yield
    finally:
        scout_apm_core_socket.SECOND = 1


@pytest.fixture
def tracked_request():
    """
    Create a temporary tracked request for the duration of the test.
    """
    request = TrackedRequest.instance()
    try:
        yield request
    finally:
        request.finish()


@pytest.fixture
def tracked_requests():
    """
    Gather all TrackedRequests that are buffered during a test into a list.
    """
    requests = []

    @wrapt.decorator
    def capture_requests(wrapped, instance, args, kwargs):
        if instance.is_real_request and not instance.is_ignored():
            requests.append(instance)
        return wrapped(*args, **kwargs)

    orig = TrackedRequest.finish
    TrackedRequest.finish = capture_requests(orig)
    try:
        yield requests
    finally:
        TrackedRequest.finish = orig
