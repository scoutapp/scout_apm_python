# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import scout_apm.sqlalchemy


def instrument_sqlalchemy(db):
    scout_apm.sqlalchemy.instrument_sqlalchemy(db.engine)
