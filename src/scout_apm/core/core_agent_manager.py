from __future__ import absolute_import

# Python Built-Ins
import hashlib
import json
import logging
import os
import subprocess
import tarfile
import time

# 3rd Party
import requests

# APM Modules
from scout_apm.core.context import AgentContext

# Logging
logger = logging.getLogger(__name__)


class CoreAgentManager:
    def __init__(self):
        self.core_agent_bin_path = None
        self.core_agent_bin_version = None
        self.core_agent_dir = '{}/{}'.format(AgentContext.instance.config.value('core_agent_dir'),
                                             AgentContext.instance.config.core_agent_full_name())
        self.downloader = CoreAgentDownloader(self.core_agent_dir,
                                              AgentContext.instance.config.core_agent_full_name())

    def launch(self):
        if AgentContext.instance.config.value('core_agent_launch') is not True:
            logger.debug("Not attempting to launch Core Agent "
                         "due to 'core_agent_launch' setting.")
            return

        if self.verify() is not True:
            if AgentContext.instance.config.value('core_agent_download') is True:
                self.download()
            else:
                logger.debug("Not attempting to download Core Agent due "
                             "to 'core_agent_download' setting.")

        if self.verify() is not True:
            logger.debug("Failed to verify Core Agent. "
                         "Not launching Core Agent.")
            return False

        return self.run()

    def download(self):
        self.downloader.download()

    def run(self):
        try:
            process = subprocess.Popen(
                    self.agent_binary() +
                    self.daemonize_flag() +
                    self.log_level() +
                    self.log_file() +
                    self.config_file() +
                    self.socket_path()
                    )
            process.wait()
        except Exception as e:
            # TODO detect failute of launch properly
            logger.error('Error running Core Agent: %s', repr(e))
            return False
        return True

    def agent_binary(self):
        return [self.core_agent_bin_path, 'start']

    def daemonize_flag(self):
        return ['--daemonize', 'true']

    def socket_path(self):
        socket_path = AgentContext.instance.config.value('socket_path')
        return ['--socket', socket_path]

    def log_level(self):
        level = AgentContext.instance.config.value('log_level')
        return ['--log-level', level]

    def log_file(self):
        path = AgentContext.instance.config.value('log_file')
        if path is not None:
            return ['--log-file', path]
        else:
            return []

    def config_file(self):
        path = AgentContext.instance.config.value('config_file')
        if path is not None:
            return ['--config-file', path]
        else:
            return []

    def verify(self):
        manifest = CoreAgentManifest(self.core_agent_dir + '/manifest.json')
        if manifest.is_valid() is not True:
            logger.debug('Core Agent verification failed: '
                         'CoreAgentManifest is not valid.')
            self.core_agent_bin_path = None
            self.core_agent_bin_version = None
            return False

        bin_path = self.core_agent_dir + '/' + manifest.bin_name
        if SHA256.digest(bin_path) == manifest.sha256:
            self.core_agent_bin_path = bin_path
            self.core_agent_bin_version = manifest.bin_version
            return True
        else:
            logger.debug('Core Agent verification failed: SHA mismatch.')
            self.core_agent_bin_path = None
            self.core_agent_bin_version = None
            return False


class CoreAgentDownloader():
    def __init__(self, download_destination, core_agent_full_name):
        self.stale_download_secs = 120
        self.destination = download_destination
        self.core_agent_full_name = core_agent_full_name
        self.package_location = self.destination + '/{}.tgz'.format(self.core_agent_full_name)
        self.download_lock_path = self.destination + '/download.lock'
        self.download_lock_fd = None

    def download(self):
        self.create_core_agent_dir()
        self.obtain_download_lock()
        if self.download_lock_fd is not None:
            try:
                self.download_package()
                self.untar()
            except OSError as e:
                logger.error('Exception raised while '
                             'downloading Core Agent: %s', repr(e))
            finally:
                self.release_download_lock()

    def create_core_agent_dir(self):
        try:
            os.makedirs(self.destination, 0o700)
        except OSError:
            pass

    def obtain_download_lock(self):
        self.clean_stale_download_lock()
        try:
            self.download_lock_fd = os.open(self.download_lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NONBLOCK)
        except OSError as e:
            logger.debug("Could not obtain download lock on %s: %s",
                         self.download_lock_path,
                         repr(e))
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
        logger.debug('Downloading: {full_url} to {filepath}'.format(
            full_url=self.full_url(),
            filepath=self.package_location))
        req = requests.get(self.full_url(), stream=True)
        with open(self.package_location, 'wb') as f:
            for chunk in req.iter_content(1024 * 1000):
                f.write(chunk)

    def untar(self):
        t = tarfile.open(self.package_location, 'r')
        t.extractall(self.destination)

    def full_url(self):
        return '{root_url}/{core_agent_full_name}.tgz'.format(
                root_url=self.root_url(),
                core_agent_full_name=self.core_agent_full_name)

    def root_url(self):
        return AgentContext.instance.config.value('download_url')


class CoreAgentManifest:
    def __init__(self, path):
        self.manifest_path = path
        self.bin_name = None
        self.bin_version = None
        self.sha256 = None
        self.valid = False
        try:
            self.parse()
        except (ValueError, TypeError, OSError, IOError) as e:
            logger.debug('Error parsing Core Agent Manifest: %s', repr(e))

    def parse(self):
        logger.debug('Parsing Core Agent'
                     ' manifest path: %s', self.manifest_path)
        with open(self.manifest_path) as manifest_file:
            self.raw = manifest_file.read()
            self.json = json.loads(self.raw)
            self.version = self.json['version']
            self.bin_version = self.json['core_agent_version']
            self.bin_name = self.json['core_agent_binary']
            self.sha256 = self.json['core_agent_binary_sha256']
            self.valid = True
            logger.debug("Core Agent manifest json: %s", self.json)

    def is_valid(self):
        return self.valid


class SHA256:
    @staticmethod
    def digest(filename, block_size=65536):
        try:
            sha256 = hashlib.sha256()
            with open(filename, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    sha256.update(block)
            return sha256.hexdigest()
        except OSError as e:
            logger.debug('Error on digest: %s', repr(e))
            return None
