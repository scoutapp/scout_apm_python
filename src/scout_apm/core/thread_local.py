from __future__ import absolute_import, division, print_function, unicode_literals

import threading


class ThreadLocalSingleton(object):
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls, *args, **kwargs):
        with cls._instance_lock:
            # The thread local dict doesn't exist at all.
            # Need to create both it and the instance.
            if not hasattr(cls, "_thread_lookup"):
                cls.__new_instance(args, kwargs)
                return cls._thread_lookup.instance

            # Somehow we have the thread local dict, but failed
            # to make the instance. Just reinitialize both.
            if not hasattr(cls._thread_lookup, "instance"):
                cls.__new_instance(args, kwargs)
                return cls._thread_lookup.instance

            # The instance is None, so we'll need to recreate it
            # (and the thread local dict too).
            if cls._thread_lookup.instance is None:
                cls.__new_instance(args, kwargs)
                return cls._thread_lookup.instance

            # We made it through the checks, return the instance
            # that we know exists.
            return cls._thread_lookup.instance

    # Releasing is under the same lock as creating,
    # so it shouldn't step on each other.
    def release(self):
        with self.__class__._instance_lock:
            if getattr(self.__class__._thread_lookup, "instance", None) is self:
                self.__class__._thread_lookup.instance = None

    @classmethod
    def __new_instance(cls, *args, **kwargs):
        cls._thread_lookup = threading.local()
        cls._thread_lookup.instance = cls(args, kwargs)
