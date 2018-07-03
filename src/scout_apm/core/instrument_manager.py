import importlib

class InstrumentManager:
    def __init__(self):
        pass

    def install(self, module_name, klass=None, *args, **kwargs):
        try:
            installable = importlib.import_module(module_name)
            if klass is not None:
                installable = getattr(installable, klass)
                installable = installable(*args, **kwargs)

            result = getattr(installable, 'install')()
            return result
        except Exception:
            return False

    def is_disabled(self, module_name):
        #  if config says its turned off:
        #      return True

        return False
