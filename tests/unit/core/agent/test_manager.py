# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import errno
import logging

from scout_apm.core.agent.manager import (
    CoreAgentManager,
    get_socket_path,
    parse_manifest,
)
from scout_apm.core.config import scout_config
from tests.compat import mock


class TestCoreAgentManager(object):
    def test_socket_path_path(self):
        scout_config.set(core_agent_socket_path="/tmp/foo.sock")

        try:
            result = CoreAgentManager().socket_path()
        finally:
            scout_config.reset_all()

        assert result == ["--socket", "/tmp/foo.sock"]

    def test_socket_path_tcp(self):
        scout_config.set(core_agent_socket_path="tcp://127.0.0.1:7894")

        try:
            result = CoreAgentManager().socket_path()
        finally:
            scout_config.reset_all()

        assert result == ["--tcp", "127.0.0.1:7894"]

    def test_log_level(self):
        scout_config.set(core_agent_log_level="foo")

        try:
            result = CoreAgentManager().log_level()
        finally:
            scout_config.reset_all()

        assert result == ["--log-level", "foo"]

    def test_log_level_old_name_takes_precedence(self):
        scout_config.set(log_level="foo", core_agent_log_level="bar")

        try:
            result = CoreAgentManager().log_level()
        finally:
            scout_config.reset_all()

        assert result == ["--log-level", "foo"]

    def test_log_file(self):
        scout_config.set(core_agent_log_file="foo")

        try:
            result = CoreAgentManager().log_file()
        finally:
            scout_config.reset_all()

        assert result == ["--log-file", "foo"]

    def test_log_file_old_name_takes_precedence(self):
        scout_config.set(log_file="foo", core_agent_log_file="bar")

        try:
            result = CoreAgentManager().log_file()
        finally:
            scout_config.reset_all()

        assert result == ["--log-file", "foo"]

    def test_config_file(self):
        scout_config.set(core_agent_config_file="foo")

        try:
            result = CoreAgentManager().config_file()
        finally:
            scout_config.reset_all()

        assert result == ["--config-file", "foo"]

    def test_config_file_old_name_takes_precedence(self):
        scout_config.set(config_file="foo", core_agent_config_file="bar")

        try:
            result = CoreAgentManager().config_file()
        finally:
            scout_config.reset_all()

        assert result == ["--config-file", "foo"]


class TestParseManifest(object):
    def test_fail_does_not_exist(self, caplog, tmp_path):
        filename = str(tmp_path / "does-not-exist.json")

        result = parse_manifest(filename)

        assert result is None
        assert caplog.record_tuples == [
            (
                "scout_apm.core.agent.manager",
                logging.DEBUG,
                "Core Agent Manifest does not exist at " + filename,
            )
        ]

    def test_fail_other_open_error(self, caplog, tmp_path):
        filename = str(tmp_path / "does-not-exist.json")
        mock_open = mock.patch(
            "scout_apm.core.agent.manager.open",
            create=True,
            side_effect=OSError(errno.EACCES),
        )

        with mock_open:
            result = parse_manifest(filename)

        assert result is None
        assert caplog.record_tuples == [
            (
                "scout_apm.core.agent.manager",
                logging.DEBUG,
                "Error opening Core Agent Manifest at " + filename,
            )
        ]

    def test_fail_core_agent_binary_not_string(self, caplog, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text('{"core_agent_binary": 1}')

        result = parse_manifest(str(manifest))

        assert result is None
        assert len(caplog.record_tuples) == 2
        assert caplog.record_tuples[1] == (
            "scout_apm.core.agent.manager",
            logging.DEBUG,
            "Error parsing Core Agent Manifest",
        )

    def test_fail_core_agent_version_not_string(self, caplog, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text('{"core_agent_binary": "", "core_agent_version": 1}')

        result = parse_manifest(str(manifest))

        assert result is None
        assert len(caplog.record_tuples) == 2
        assert caplog.record_tuples[1] == (
            "scout_apm.core.agent.manager",
            logging.DEBUG,
            "Error parsing Core Agent Manifest",
        )

    def test_fail_core_agent_binary_sha256_not_string(self, caplog, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            '{"core_agent_binary": "", "core_agent_version": "", '
            + '"core_agent_binary_sha256": 1}'
        )

        result = parse_manifest(str(manifest))

        assert result is None
        assert len(caplog.record_tuples) == 2
        assert caplog.record_tuples[1] == (
            "scout_apm.core.agent.manager",
            logging.DEBUG,
            "Error parsing Core Agent Manifest",
        )

    def test_success(self, caplog, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            '{"core_agent_binary": "bin", "core_agent_version": "1.2.3", '
            + '"core_agent_binary_sha256": "abc"}'
        )

        result = parse_manifest(str(manifest))

        assert result.bin_name == "bin"
        assert result.bin_version == "1.2.3"
        assert result.sha256 == "abc"
        logger, level, message = caplog.record_tuples[0]
        assert logger == "scout_apm.core.agent.manager"
        assert level == logging.DEBUG
        assert message.startswith("Core Agent manifest json: ")


class TestGetSocketPath(object):
    def test_from_socket_path(self):
        scout_config.set(socket_path="/tmp/my.sock")
        try:
            assert get_socket_path() == "/tmp/my.sock"
        finally:
            scout_config.reset_all()

    def test_from_core_agent_socket_path(self):
        scout_config.set(core_agent_socket_path="/tmp/that.sock")
        try:
            assert get_socket_path() == "/tmp/that.sock"
        finally:
            scout_config.reset_all()

    def test_not_tcp(self):
        scout_config.set(core_agent_socket_path="/tmp/that.sock")
        try:
            assert not get_socket_path().is_tcp
        finally:
            scout_config.reset_all()

    def test_tcp(self):
        scout_config.set(core_agent_socket_path="tcp://127.0.0.1:1234")
        try:
            assert get_socket_path().is_tcp
        finally:
            scout_config.reset_all()
