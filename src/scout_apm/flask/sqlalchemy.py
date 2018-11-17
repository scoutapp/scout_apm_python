from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

import scout_apm.sqlalchemy
from scout_apm.core.monkey import monkeypatch_method
from scout_apm.core.tracked_request import TrackedRequest


def instrument_sqlalchemy(db):
    @monkeypatch_method(SQLAlchemy)
    def get_engine(original, self, *args, **kwargs):
        engine = original(*args, **kwargs)
        scout_apm.sqlalchemy.instrument_sqlalchemy(engine)
        return engine
