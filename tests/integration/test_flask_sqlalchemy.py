from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from flask_sqlalchemy import SQLAlchemy

from scout_apm.flask.sqlalchemy import instrument_sqlalchemy

from .test_flask import app_with_scout


@contextmanager
def conn_with_scout():
    with app_with_scout() as app:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        db = SQLAlchemy(app)
        # Setup according to http://docs.scoutapm.com/#flask-sqlalchemy
        instrument_sqlalchemy(db)
        conn = db.engine.connect()
        try:
            yield conn
        finally:
            conn.close()


def test_hello():
    with conn_with_scout() as conn:
        result = conn.execute("SELECT 'Hello World!'")
        assert list(result) == [("Hello World!",)]
