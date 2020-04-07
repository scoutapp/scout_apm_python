# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import json
import logging
import os
import subprocess
import tarfile
import time

from urllib3.exceptions import HTTPError

from scout_apm.compat import urllib3_cert_pool_manager
from scout_apm.core.config import scout_config

logger = logging.getLogger(__name__)


class CoreAgentManager(object):
    def __init__(self):
        self.core_agent_bin_path = None
        self.core_agent_bin_version = None
        self.core_agent_dir = "{}/{}".format(
            scout_config.value("core_agent_dir"),
            scout_config.value("core_agent_full_name"),
        )
        self.downloader = CoreAgentDownloader(
            self.core_agent_dir, scout_config.value("core_agent_full_name")
        )

    def launch(self):
        if not scout_config.value("core_agent_launch"):
            logger.debug(
                "Not attempting to launch Core Agent "
                "due to 'core_agent_launch' setting."
            )
            return False

        if not self.verify():
            if not scout_config.value("core_agent_download"):
                logger.debug(
                    "Not attempting to download Core Agent due "
                    "to 'core_agent_download' setting."
                )
                return False

            self.download()

            if not self.verify():
                logger.debug("Failed to verify Core Agent. Not launching Core Agent.")
                return False

        return self.run()

    def download(self):
        self.downloader.download()

    def run(self):
        try:
            with open(os.devnull) as devnull:
                subprocess.check_call(
                    (
                        self.agent_binary()
                        + self.daemonize_flag()
                        + self.log_level()
                        + self.log_file()
                        + self.config_file()
                        + self.socket_path()
                    ),
                    close_fds=True,
                    stdout=devnull,
                )
        except Exception:
            # TODO detect failure of launch properly
            logger.exception("Error running Core Agent")
            return False
        return True

    def agent_binary(self):
        return [self.core_agent_bin_path, "start"]

    def daemonize_flag(self):
        return ["--daemonize", "true"]

    def socket_path(self):
        # Old deprecated name "socket_path"
        socket_path = scout_config.value("socket_path")
        if socket_path is None:
            socket_path = scout_config.value("core_agent_socket_path")
        return ["--socket", socket_path]

    def log_level(self):
        # Old deprecated name "log_level"
        log_level = scout_config.value("log_level")
        if log_level is None:
            log_level = scout_config.value("core_agent_log_level")
        return ["--log-level", log_level]

    def log_file(self):
        # Old deprecated name "log_file"
        path = scout_config.value("log_file")
        if path is None:
            path = scout_config.value("core_agent_log_file")

        if path is not None:
            return ["--log-file", path]
        else:
            return []

    def config_file(self):
        # Old deprecated name "config_file"
        path = scout_config.value("config_file")
        if path is None:
            path = scout_config.value("core_agent_config_file")

        if path is not None:
            return ["--config-file", path]
        else:
            return []

    def verify(self):
        manifest = CoreAgentManifest(self.core_agent_dir + "/manifest.json")
        if not manifest.is_valid():
            logger.debug(
                "Core Agent verification failed: CoreAgentManifest is not valid."
            )
            self.core_agent_bin_path = None
            self.core_agent_bin_version = None
            return False

        bin_path = self.core_agent_dir + "/" + manifest.bin_name
        if sha256_digest(bin_path) == manifest.sha256:
            self.core_agent_bin_path = bin_path
            self.core_agent_bin_version = manifest.bin_version
            return True
        else:
            logger.debug("Core Agent verification failed: SHA mismatch.")
            self.core_agent_bin_path = None
            self.core_agent_bin_version = None
            return False


class CoreAgentDownloader(object):
    def __init__(self, download_destination, core_agent_full_name):
        self.stale_download_secs = 120
        self.destination = download_destination
        self.core_agent_full_name = core_agent_full_name
        self.package_location = self.destination + "/{}.tgz".format(
            self.core_agent_full_name
        )
        self.download_lock_path = self.destination + "/download.lock"
        self.download_lock_fd = None

    def download(self):
        self.create_core_agent_dir()
        self.obtain_download_lock()
        if self.download_lock_fd is not None:
            try:
                downloaded = self.download_package()
                if downloaded:
                    self.untar()
            except (OSError, HTTPError):
                logger.exception("Exception raised while downloading Core Agent")
            finally:
                self.release_download_lock()

    def create_core_agent_dir(self):
        try:
            os.makedirs(self.destination, scout_config.core_agent_permissions())
        except OSError:
            pass

    def obtain_download_lock(self):
        self.clean_stale_download_lock()
        try:
            self.download_lock_fd = os.open(
                self.download_lock_path,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NONBLOCK,
            )
        except OSError as exc:
            logger.debug(
                "Could not obtain download lock on %s",
                self.download_lock_path,
                exc_info=exc,
            )
            self.download_lock_fd = None

    def clean_stale_download_lock(self):
        try:
            delta = time.time() - os.stat(self.download_lock_path).st_ctime
            if delta > self.stale_download_secs:
                logger.debug("Clearing stale download lock file.")
                os.unlink(self.download_lock_path)
        except OSError:
            pass

    def release_download_lock(self):
        if self.download_lock_fd is not None:
            os.unlink(self.download_lock_path)
            os.close(self.download_lock_fd)

    def download_package(self):
        full_url = self.full_url()
        logger.debug("Downloading: %s to %s", full_url, self.package_location)
        http = urllib3_cert_pool_manager()
        response = http.request(
            "GET", full_url, preload_content=False, timeout=10.0, retries=3
        )
        try:
            if response.status != 200:
                return False
            with open(self.package_location, "wb") as fp:
                for chunk in response.stream():
                    fp.write(chunk)
        finally:
            response.release_conn()
        return True

    def untar(self):
        t = tarfile.open(self.package_location, "r")
        t.extractall(self.destination)

    def full_url(self):
        return "{root_url}/{core_agent_full_name}.tgz".format(
            root_url=self.root_url(), core_agent_full_name=self.core_agent_full_name
        )

    def root_url(self):
        return scout_config.value("download_url")


class CoreAgentManifest(object):
    def __init__(self, path):
        self.manifest_path = path
        self.bin_name = None
        self.bin_version = None
        self.sha256 = None
        self.valid = False
        try:
            self.parse()
        # noqa for this issue: https://github.com/PyCQA/flake8-bugbear/issues/110
        except (ValueError, TypeError, OSError, IOError) as exc:  # noqa: B014
            logger.debug("Error parsing Core Agent Manifest", exc_info=exc)

    def parse(self):
        logger.debug("Parsing Core Agent manifest path: %s", self.manifest_path)
        with open(self.manifest_path) as manifest_file:
            self.raw = manifest_file.read()
            self.json = json.loads(self.raw)
            self.version = self.json["version"]
            self.bin_version = self.json["core_agent_version"]
            self.bin_name = self.json["core_agent_binary"]
            self.sha256 = self.json["core_agent_binary_sha256"]
            self.valid = True
            logger.debug("Core Agent manifest json: %s", self.json)

    def is_valid(self):
        return self.valid


def sha256_digest(filename, block_size=65536):
    try:
        sha256 = hashlib.sha256()
        with open(filename, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                sha256.update(block)
        return sha256.hexdigest()
    except OSError as exc:
        logger.debug("Error on digest", exc_info=exc)
        return None
