from __future__ import absolute_import

import logging

logger = logging.getLogger(__name__)


from scout_apm.core.tracked_request import TrackedRequest
from scout_apm.core.monkey import monkeypatch_method

class Instrument:
    PYMONGO_METHODS = ['aggregate', 'bulk_write', 'count',
                       'create_index', 'create_indexes', 'delete_many',
                       'delete_one', 'distinct', 'drop',
                       'drop_index', 'drop_indexes', 'ensure_index',
                       'find_and_modify', 'find_one', 'find_one_and_delete',
                       'find_one_and_replace', 'find_one_and_update', 'group',
                       'inline_map_reduce', 'insert', 'insert_many',
                       'insert_one', 'map_reduce', 'reindex',
                       'remove', 'rename', 'replace_one',
                       'save', 'update', 'update_many',
                       'update_one']

    def __init__(self):
        self.installed = False

    def installable(self):
        try:
            from pymongo.collection import Collection
        except ImportError:
            logger.info("Unable to import for PyMongo instruments")
            return False
        if self.installed:
            logger.warn("PyMongo Instruments are already installed.")
            return False
        return True


    def install(self):
        if not self.installable():
            logger.info("PyMongo instruments are not installable. Skipping.")
            return False

        self.installed = True

        try:
            from pymongo.collection import Collection
        except ImportError:
            logger.info("Unable to import for PyMongo instruments. Instrument install failed.")
            return False

        for method_str in self.__class__.PYMONGO_METHODS:
            try:
                code_str = """
@monkeypatch_method(Collection)
def {method_str}(original, self, *args, **kwargs):
    tr = TrackedRequest.instance()
    name = '/'.join(['MongoDB', self.name, '{camel_name}'])
    span = tr.start_span(operation=name, ignore_children=True)
    span.tag('name', self.name)

    try:
        return original(*args, **kwargs)
    finally:
        tr.stop_span()
""".format(method_str=method_str, camel_name=''.join(c.title() for c in method_str.split('_')))

                exec(code_str)
                logger.info('Instrumented PyMongo Collection.{}'.format(method_str))

            except Exception as e:
                logger.warn('Unable to instrument for PyMongo Collection.{}: {}'.format(method_str, repr(e)))
        return True
