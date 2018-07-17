import importlib
import logging

from scout_apm.core.context import AgentContext


logger = logging.getLogger(__name__)


class InstrumentManager:
    INSTRUMENT_NAMESPACE = 'scout_apm.instruments'
    DEFAULT_INSTRUMENTS = ['jinja2', 'pymongo', 'redis',
                           'urllib3', 'elasticsearch']

    def install(self, module_name, klass="Instrument", *args, **kwargs):
        try:
            installable = importlib.import_module(module_name)
            installable = getattr(installable, klass)
            installable = installable(*args, **kwargs)

            result = getattr(installable, 'install')()
            return result
        except Exception as e:
            logger.info('Exception while installing instrument {}: {}'.format(module_name, repr(e)))
            return False

    def install_all(self):
        for module_name in self.__class__.DEFAULT_INSTRUMENTS:
            if self.is_disabled(module_name):
                logger.info('{} instruments are disabled. Skipping.'.format(module_name))
                continue
            self.install('{}.{}'.format(self.__class__.INSTRUMENT_NAMESPACE, module_name))

    def is_disabled(self, module_name):
        disabled = AgentContext.instance.config.value('disabled_instruments')
        if module_name in disabled:
            return True
