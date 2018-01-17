import platform
import resource


class Memory(object):
    # Account for Darwin returning maxrss in bytes and Linux in KB. Used by
    # the slow converters. Doesn't feel like this should go here
    # though...more of a utility.
    @classmethod
    def rss_to_mb(cls, rss):
        kilobyte_adjust = 1024 if (platform.system == 'Darwin') else 1
        return float(rss) / 1024 / kilobyte_adjust

    @classmethod
    def rss(cls):
        return resource.getrusage(resource.RUSAGE_SELF).maxrss

    @classmethod
    def rss_in_mb(cls):
        return cls.rss_to_mb(cls.rss())

    def metric_type(self):
        return "Memory"

    def metric_name(self):
        return "Physical"

    def human_name(self):
        return "Process Memory"

    def metrics(self):
        """
        TODO: after implementing metrics collector,
        make sure this returns compatible metrics
        """
        return None

    def run(self):
        res = self.__class__.rss_in_mb()
        print("{human_name}: #{res}").format(human_name=self.human_name(),
                                             res=res)
