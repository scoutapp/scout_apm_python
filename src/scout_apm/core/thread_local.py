from __future__ import absolute_import

import threading


class ThreadLocalSingleton(object):
    @classmethod
    def instance(cls, *args, **kwargs):
        if not hasattr(cls, '_thread_lookup'):
            cls.__new_instance(args, kwargs)
        elif not hasattr(cls._thread_lookup, 'instance'):
            cls.__new_instance(args, kwargs)
        elif cls._thread_lookup.instance is None:
            cls.__new_instance(args, kwargs)
        return cls._thread_lookup.instance

    @classmethod
    def __new_instance(cls, *args, **kwargs):
        cls._thread_lookup = threading.local()
        cls._thread_lookup.instance = cls(args, kwargs)

    def release(self):
            if getattr(self.__class__._thread_lookup,
                       'instance',
                       None) is self:
                self.__class__._thread_lookup.instance = None
