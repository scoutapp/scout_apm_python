# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.template import Library, Template, defaulttags
from django.template.loader_tags import BlockNode

from scout_apm.core.stacktracer import trace_function, trace_method

logger = logging.getLogger(__name__)

register = Library()


class DecoratingParserProxy(object):  # pragma: no cover
    """
    Mocks out the django template parser, passing templatetags through but
    first wrapping them to include performance data
    """

    def __init__(self, parser):
        self.parser = parser

    def add_library(self, library):
        wrapped_library = Library()
        wrapped_library.filters = library.filters
        for name, tag_compiler in library.tags.items():
            wrapped_library.tags[name] = self.wrap_compile_function(name, tag_compiler)
        self.parser.add_library(wrapped_library)

    def wrap_compile_function(self, name, tag_compiler):
        def compile(*args, **kwargs):
            node = tag_compiler(*args, **kwargs)
            node.render = trace_function(node.render, ("Template/Tag", {"name": name}))
            return node

        return compile


@register.tag
def load(parser, token):  # pragma: no cover
    decorating_parser = DecoratingParserProxy(parser)
    return defaulttags.load(decorating_parser, token)


def install_template_instrumentation():
    if getattr(install_template_instrumentation, "installed", False):
        return
    install_template_instrumentation.installed = True

    # Our eventual aim is to patch the render() method on the Node objects
    # corresponding to custom template tags. However we have to jump through
    # a number of hoops in order to get access to the object.
    #
    # 1. Add ourselves to the set of built in template tags
    #    This allows us to replace the 'load' template tag which controls
    #    the loading of custom template tags
    # 2. Delegate to default load with replaced parser
    #    We provide our own parser class so we can catch and intercept
    #    calls to add_library.
    # 3. add_library receives a library of template tags
    #    It iterates through each template tag, wrapping its compile function
    # 4. compile is called as part of compiling the template
    #    Our wrapper is called instead of the original templatetag compile
    #    function. We delegate to the original function, but then modify
    #    the resulting object by wrapping its render() function. This
    #    render() function is what ends up being timed and appearing in the
    #    tree.

    # XXX: Stopped working in Django 1.9
    #  add_to_builtins('apm.instruments.view')

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
