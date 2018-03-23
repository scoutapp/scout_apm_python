import logging
from datetime import datetime, timedelta
from textwrap import dedent

import psutil

# Logging
logger = logging.getLogger(__name__)


class Cpu(object):
    def __init__(self):
        self.last_run = datetime.now()
        self.last_cpu_times = psutil.Process().cpu_times()
        self.num_processors = psutil.cpu_count()

    def metric_type(self):
        return "CPU"

    def metric_name(self):
        return "Utilization"

    def human_name(self):
        return "Process CPU"

    def run(self):
        now = datetime.now()
        process = psutil.Process() # get a handle on the current process
        cpu_times = process.cpu_times()

        wall_clock_elapsed = now - self.last_run
        if wall_clock_elapsed < timedelta(0):
            self.save_times(now, cpu_times)
            logger.debug(dedent(
                         """
                         {human_name}: Negative time elapsed.
                         now: {now},
                         last_run: {last_run},
                         total time: {wall_clock_elapsed}.
                         """
                         ).format(human_name=self.human_name(),
                                  now=now,
                                  last_run=self.last_run))
            return None

        utime_elapsed = cpu_times.user - self.last_cpu_times.user
        stime_elapsed = cpu_times.system - self.last_cpu_times.system
        process_elapsed = utime_elapsed + stime_elapsed

        # This can happen right after a fork.  This class starts up in
        # pre-fork, records {u,s}time, then forks. This resets {u,s}time to 0
        if process_elapsed < 0:
            self.save_times(now, cpu_times)
            logger.debug(dedent(
                         """
                         {human_name}: Negative process time elapsed.
                         utime: {utime_elapsed},
                         stime: {stime_elapsed},
                         total time: {process_elapsed}.
                         This is normal to see when starting a
                         forking web server.
                         """
                        ).format(human_name=self.human_name(),
                                 utime_elapsed=utime_elapsed,
                                 stime_elapsed=stime_elapsed,
                                 process_elapsed=process_elapsed))
            return None

        # Normalized to # of processors
        normalized_wall_clock_elapsed = (wall_clock_elapsed * self.num_processors).total_seconds()

        # If somehow we run for 0 seconds between calls, don't try to divide by 0
        res = None
        if normalized_wall_clock_elapsed == 0:
            res = 0
        else:
            res = (process_elapsed / normalized_wall_clock_elapsed)*100

        if res < 0:
            self.save_times(now, cpu_times)
            logger.debug(dedent(
                         """
                         {human_name}: Negative CPU.
                         {process_elapsed} / {normalized_wall_clock_elapsed} * 100 ==> {res}
                         """
                         ).format(human_name=self.human_name(),
                                  process_elapsed=process_elapsed,
                                  normalized_wall_clock_elapsed=normalized_wall_clock_elapsed,
                                  res=res))
            return None

        self.save_times(now, cpu_times)

        logger.debug(dedent(
                     """
                     {human_name}: {res} [{num_processors} CPU(s)]
                     """
                     ).format(human_name=self.human_name(),
                              res=res,
                              num_processors=self.num_processors))

        return res

    def save_times(self, now, cpu_times):
        self.last_run = now
        self.cpu_times = cpu_times
