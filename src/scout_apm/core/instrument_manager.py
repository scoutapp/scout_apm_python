import importlib

from scout_apm.core.context import AgentContext


class InstrumentManager:
    def install(self, module_name, klass="Instrument", *args, **kwargs):
        try:
            # Configuration can disable individual instruments
            #  if self.is_disabled(module_name):
            #      return False

            installable = importlib.import_module(module_name)
            installable = getattr(installable, klass)
            installable = installable(*args, **kwargs)

            result = getattr(installable, 'install')()
            return result
        except Exception:
            return False

    def install_all(self):
        self.install("scout_apm.instruments.jinja2")
        self.install("scout_apm.instruments.mongo")
        self.install("scout_apm.instruments.reqwests")

    def is_disabled(self, module_name):
        #  disabled = AgentContext.instance.config.value('disabled_instruments')
        #  if in_list:
        #      return True
        return False

