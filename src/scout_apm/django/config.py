from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.conf import settings

from scout_apm.core.config import ScoutConfig

logger = logging.getLogger(__name__)


class ConfigAdapter(object):
    @classmethod
    def install(cls):
        configs = {}
        if getattr(settings, "BASE_DIR", None) is not None:
            configs["application_root"] = settings.BASE_DIR
        for name in dir(settings):
            if name.startswith("SCOUT_"):
                value = getattr(settings, name)
                clean_name = name.replace("SCOUT_", "").lower()
                configs[clean_name] = value
        ScoutConfig.set(**configs)
