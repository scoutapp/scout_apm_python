#!/usr/bin/env python
from __future__ import absolute_import
import argparse
import logging


def download(**kwargs):
    from scout_apm.core import CoreAgentManager
    core_agent_manager = CoreAgentManager()
    core_agent_manager.download()


def launch(**kwargs):
    from scout_apm.core import CoreAgentManager
    core_agent_manager = CoreAgentManager()
    core_agent_manager.launch()


def main(**kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="count")

    subparsers = parser.add_subparsers(dest='subparser')

    download_parser = subparsers.add_parser('download')

    launch_parser = subparsers.add_parser('launch')

    args = parser.parse_args()

    if args.verbose is not None:
        if args.verbose >= 2:
            logging.basicConfig(level=getattr(logging, 'DEBUG', None))
        elif args.verbose == 1:
            logging.basicConfig(level=getattr(logging, 'INFO', None))

    kwargs = vars(args)
    globals()[kwargs.pop('subparser')](**kwargs)
