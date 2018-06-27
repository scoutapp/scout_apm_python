from __future__ import absolute_import

import logging
import os

logger = logging.getLogger(__name__)


# Note that this is called from Config Defaults, which is looked up after the
# configs from environment variables. If you set SCOUT_REVISION_SHA, it will be
# picked up in that step of config, not here.
#
# Similarly, this can be overriden by the code level configuration (from Django
# configs or similar) by using the "revision_sha" key.
class GitRevision():
    def detect(self):
        sha = self.detect_from_env_var() or self.detect_from_heroku()
        return sha or ''

    def detect_from_heroku(self):
        return os.environ.get('HEROKU_SLUG_COMMIT')

    def detect_from_env_var(self):
        return os.environ.get('SCOUT_REVISION_SHA')
