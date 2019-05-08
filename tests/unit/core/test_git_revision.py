# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import os

from scout_apm.core.git_revision import GitRevision

os.environ.pop("HEROKU_SLUG_COMMIT", None)
os.environ.pop("SCOUT_REVISION_SHA", None)


def test_detect_from_scout_env():
    os.environ["SCOUT_REVISION_SHA"] = "FROM_SCOUT_ENV"
    try:
        assert GitRevision().detect() == "FROM_SCOUT_ENV"
    finally:
        del os.environ["SCOUT_REVISION_SHA"]


def test_detect_from_heroku_slug():
    os.environ["HEROKU_SLUG_COMMIT"] = "FROM_HEROKU_SLUG"
    try:
        assert GitRevision().detect() == "FROM_HEROKU_SLUG"
    finally:
        del os.environ["HEROKU_SLUG_COMMIT"]


def test_detect_nothing_returns_empty_string():
    assert GitRevision().detect() == ""


def test_scout_env_outranks_heroku_slug():
    os.environ["SCOUT_REVISION_SHA"] = "FROM_SCOUT_ENV"
    os.environ["HEROKU_SLUG_COMMIT"] = "FROM_HEROKU_SLUG"
    try:
        assert GitRevision().detect() == "FROM_SCOUT_ENV"
    finally:
        del os.environ["SCOUT_REVISION_SHA"]
        del os.environ["HEROKU_SLUG_COMMIT"]
