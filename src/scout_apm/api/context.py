from __future__ import absolute_import, division, print_function, unicode_literals

from scout_apm.core.tracked_request import TrackedRequest


class Context(object):
    @staticmethod
    def add(key, value):
        """Adds context to the currently executing request.

        :key: Any String identifying the request context.
              Example: "user_ip", "plan", "alert_count"
        :value: Any json-serializable type.
              Example: "1.1.1.1", "free", 100
        :returns: nothing.
        """
        tr = TrackedRequest.instance()
        tr.tag(key, value)
