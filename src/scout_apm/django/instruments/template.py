# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.template import Template
from django.template.loader_tags import BlockNode

from scout_apm.core.stacktracer import trace_method

logger = logging.getLogger(__name__)

instrumented = False


def ensure_instrumented():
    global instrumented
    if instrumented:
        return
    instrumented = True

    @trace_method(Template)
    def __init__(self, *args, **kwargs):
        name = args[2] if len(args) >= 3 else "<Unknown Template>"
        return ("Template/Compile", {"name": name})

    @trace_method(Template)
    def render(self, *args, **kwargs):
        name = self.name if self.name is not None else "<Unknown Template>"
        return ("Template/Render", {"name": name})

    @trace_method(BlockNode, "render")
    def render_block(self, *args, **kwargs):
        return ("Block/Render", {"name": self.name})

    logger.debug("Monkey patched Templates")
