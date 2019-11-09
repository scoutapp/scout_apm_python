# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import importlib
import logging

from scout_apm.core.config import scout_config

logger = logging.getLogger(__name__)


class InstrumentManager(object):
    INSTRUMENT_NAMESPACE = "scout_apm.instruments"
    DEFAULT_INSTRUMENTS = ["pymongo", "elasticsearch"]

    def install(self, module_name, klass="Instrument", *args, **kwargs):
        try:
            installable = importlib.import_module(module_name)
            installable = getattr(installable, klass)
            installable = installable(*args, **kwargs)

            result = installable.install()
            return result
        except Exception as e:
            logger.info("Exception while installing instrument %s: %r", module_name, e)
            return False

    def install_all(self):
        for module_name in self.__class__.DEFAULT_INSTRUMENTS:
            if self.is_disabled(module_name):
                logger.info("%s instruments are disabled. Skipping.", module_name)
                continue
            self.install(
                "{}.{}".format(self.__class__.INSTRUMENT_NAMESPACE, module_name)
            )

    def is_disabled(self, module_name):
        disabled = scout_config.value("disabled_instruments")
        if module_name in disabled:
            return True
