from __future__ import absolute_import

import logging
import os

logger = logging.getLogger(__name__)


class GitRevision():
    def detect(self):
        sha = self.detect_from_env_var() or self.detect_from_heroku()
        return sha or ''

    def detect_from_heroku(self):
        if 'HEROKU_SLUG_COMMIT' in os.environ:
            return os.environ['HEROKU_SLUG_COMMIT']
        return None

    def detect_from_env_var(self):
        if 'SCOUT_REVISION_SHA' in os.environ:
            return os.environ['SCOUT_REVISION_SHA']
        return None
