# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import errno
import logging
import sys

from scout_apm.core.core_agent_manager import parse_manifest
from tests.compat import mock


class TestParseManifest(object):
    def test_fail_does_not_exist(self, caplog, tmp_path):
        filename = str(tmp_path / "does-not-exist.json")

        result = parse_manifest(filename)

        assert result is None
        assert caplog.record_tuples == [
            (
                "scout_apm.core.core_agent_manager",
                logging.DEBUG,
                "Core Agent Manifest does not exist at " + filename,
            )
        ]

    def test_fail_other_open_error(self, caplog, tmp_path):
        filename = str(tmp_path / "does-not-exist.json")
        if sys.version_info[0] == 2:
            error = IOError("Woops", errno.EACCES)
        else:
            error = OSError(errno.EACCES)

        with mock.patch("scout_apm.core.core_agent_manager.open", side_effect=error):
            result = parse_manifest(filename)

        assert result is None
        assert caplog.record_tuples == [
            (
                "scout_apm.core.core_agent_manager",
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
            "scout_apm.core.core_agent_manager",
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
            "scout_apm.core.core_agent_manager",
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
            "scout_apm.core.core_agent_manager",
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
        assert logger == "scout_apm.core.core_agent_manager"
        assert level == logging.DEBUG
        assert message.startswith("Core Agent manifest json: ")
