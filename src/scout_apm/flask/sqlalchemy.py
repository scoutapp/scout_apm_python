from __future__ import absolute_import, division, print_function, unicode_literals

from flask_sqlalchemy import SQLAlchemy

import scout_apm.sqlalchemy
from scout_apm.core.monkey import monkeypatch_method


def instrument_sqlalchemy(db):
    @monkeypatch_method(SQLAlchemy)
    def get_engine(original, self, *args, **kwargs):
        engine = original(*args, **kwargs)
        scout_apm.sqlalchemy.instrument_sqlalchemy(engine)
        return engine
