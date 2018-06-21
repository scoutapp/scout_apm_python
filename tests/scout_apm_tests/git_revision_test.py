import os

from scout_apm.core.git_revision import GitRevision


def test_detects_nothing_returns_string():
    if 'HEROKU_SLUG_COMMIT' in os.environ:
        del(os.environ['HEROKU_SLUG_COMMIT'])
    if 'SCOUT_REVISION_SHA' in os.environ:
        del(os.environ['SCOUT_REVISION_SHA'])
    assert('' == GitRevision().detect())


def test_detect_from_heroku_slug():
    os.environ['HEROKU_SLUG_COMMIT'] = 'FROM_HEROKU_SLUG'
    assert('FROM_HEROKU_SLUG' == GitRevision().detect())


def test_detect_from_scout_env():
    os.environ['SCOUT_REVISION_SHA'] = 'FROM_SCOUT_ENV'
    assert('FROM_SCOUT_ENV' == GitRevision().detect())
