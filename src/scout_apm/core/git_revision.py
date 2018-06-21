from __future__ import absolute_import

import logging
import os

logger = logging.getLogger(__name__)


class GitRevision():
    def detect(self):
        sha = self.detect_from_env_var() or self.detect_from_heroku()
        return sha or ''

    def detect_from_heroku(self):
        return os.environ.get('HEROKU_SLUG_COMMIT')

    def detect_from_env_var(self):
        return os.environ.get('SCOUT_REVISION_SHA')
