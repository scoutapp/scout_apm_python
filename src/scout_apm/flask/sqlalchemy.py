from scout_apm.core.monkey import monkeypatch_method
from scout_apm.core.tracked_request import TrackedRequest
import scout_apm.sqlalchemy

from sqlalchemy import event
from flask_sqlalchemy import SQLAlchemy

def instrument_sqlalchemy(db):
    @monkeypatch_method(SQLAlchemy)
    def get_engine(original, self, *args, **kwargs):
        engine = original(*args, **kwargs)
        scout_apm.sqlalchemy.instrument_sqlalchemy(engine)
        return engine
