# TODO:
#   * How to ask an existing agent who it is & what version
#   * Should we politely ask an existing agent to shutdown?
#   * Core agent stdin/stdout? - should close, or try to proxy back to python?
#   * Where do we download to
#   * Where do we unpack the binary
#   * What to do if we don't have the arch/version hosted?
#   * What workflow for self-launching core agent?
#   * Build script to build different versions
#   * Launch style - fork/exec w/ command line options
#   * How to shut down python
#   * Core Agent updates itself?
#   * support "download" from a local file path
#
#  Build process
#    * for each environment,
#      * build
#      * create metadata
#      * tar
#    * s3 bucket
#      * downloads.scoutapp.com/core_agent/....
#
#  scout_apm_core-latest_metadata.txt - ~1k
#  scout_apm_core-latest.tgz
#  |- scout_apm_core-1.2.3-linux-x86_64
#  |- manifest.txt
#
#     metadata something like:
#     { version: 1
#       core_binary: scout_apm_core-1.2.3-linux-x86_64
#       core_binary_sha256: 0123456ABCDEFG...
#     }
#
#
#           - detect version (default or specified in config)
#           - specify SSL CA file?
#           - where to download from/to
#           - platform
#           - architecture
#           - root url for tgz
#           - proxy (python urllib reads from http_proxy/https_proxy env var)
#           - sha256sum the downloaded file, compare to metadata
#           - launch - how?

import hashlib
import platform
import tarfile
import urllib.request
import subprocess

from scout_apm.context import agent_context
from scout_apm.socket import CoreAgentSocket
from scout_apm.commands import CoreAgentVersion, CoreAgentVersionResponse, CoreAgentShutdown


class CoreAgentManager:
    def launch(self):
        # Kill any existing core agent
        probe = CoreAgentProbe()
        if probe.is_running():
            print('Trying to shutdown an already-running CoreAgent')
            probe.shutdown()

        # Launch the CoreAgent we want
        executable = '/Users/cschneid/Projects/core-agent/target/debug/core-agent'
        self.run(executable)
        print('Launching')

    def run(self, executable):
        subprocess.Popen(
                [
                    executable, 'daemon',
                    '--api-key', 'Qnk5SKpNEeboPdeJkhae',
                    '--log-level', 'info',
                    '--app-name', 'CoreAgent'
                ])

    def download(self):
        print('Downloading: {full_url} to {filepath}'.format(
            full_url=self.full_url(),
            filepath=self.core_filepath()))
        urllib.request.urlretrieve(self.full_url(), self.core_filepath())

    def full_url(self):
        return '{root_url}/{binary_name}.tgz'.format(
                root_url=self.root_url(),
                binary_name=self.binary_name())

    def root_url(self):
        return 'https://scoutapp.com'

    def binary_name(self):
        return 'scout_apm_core-{version}-{platform}-{arch}'.format(
                version=self.core_agent_version(),
                platform=self.platform(),
                arch=self.arch())

    def platform_supported(self):
        return True

    def platform(self):
        system_name = platform.system()
        if system_name == 'Linux':
            return 'linux'
        elif system_name == 'Darwin':
            return 'darwin'
        else:
            return 'unknown'

    def arch_supported(self):
        return True

    def arch(self):
        arch = platform.machine()
        if arch == 'i386':
            return 'i386'
        elif arch == 'x86_64':
            return 'x86_64'
        else:
            return 'unknown'

    def core_filepath(self):
        return '/tmp/{binary_name}'.format(binary_name=self.binary_name())

    def core_agent_version(self):
        return 'latest'

    def untar(self):
        t = tarfile.open(self.core_filepath(), 'r')
        t.extractall('outdir')

    def sha256_sum(self):
        f = open(self.core_filepath(), 'rb')
        hash = hashlib.sha256()
        if f.multiple_chunks():
            for chunk in f.chunks():
                hash.update(chunk)
        else:
            hash.update(f.read())
        f.close()
        return hash.hexdigest()


class CoreAgentProbe():
    def is_running(self):
        return self.version() is not None

    # Returns a CoreAgentVersion or None
    def version(self):
        try:
            socket = self.build_socket()
            response = socket.send(CoreAgentVersion())
            self.version = CoreAgentVersionResponse(response).version
            print('version:', self.version)
            return self.version
        except Exception as e:
            print('Existing CoreAgent is not running')
            return None

    def shutdown(self):
        socket = self.build_socket()
        socket.send(CoreAgentShutdown())
        print('Shut down existing CoreAgent')

    def build_socket(self):
        socket_path = agent_context.config.value('core_agent_socket')
        socket = CoreAgentSocket(socket_path)
        socket.open()
        return socket


# Core Agent per app
# latest_version = CoreAgentManager().latest_version()
# probe = CoreAgentProbe(socket_path)
# version = probe.version()
# if version is not None:
#     if version.is_not_newest()
#         probe.shudown()
#
# CoreAgentManager().download()
# CoreAgentManager().unpack()
# CoreAgentManager().launch(socket_path, app_name)
#
# # when app stops
# CoreAgentManager.shutdown()
