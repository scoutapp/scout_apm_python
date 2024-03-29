# coding=utf-8

from contextlib import contextmanager

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from webtest import TestApp

from scout_apm.compat import kwargs_only
from scout_apm.flask.sqlalchemy import instrument_sqlalchemy
from tests.integration.test_flask import app_with_scout as flask_app_with_scout


@contextmanager
@kwargs_only
def app_with_scout():
    with flask_app_with_scout() as app:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db = SQLAlchemy()
        # Setup according to https://docs.scoutapm.com/#flask-sqlalchemy
        instrument_sqlalchemy(db)
        db.init_app(app)
        # Use manual context
        # https://flask-sqlalchemy.palletsprojects.com/en/latest/contexts/#manual-context
        with app.app_context():
            conn = db.engine.connect()

            @app.route("/sqlalchemy/")
            def sqlalchemy():
                result = conn.execute(text("SELECT 'Hello from the DB!'"))
                return list(result)[0][0]

            try:
                yield app
            finally:
                conn.close()


def test_sqlalchemy(tracked_requests):
    with app_with_scout() as app:
        response = TestApp(app).get("/sqlalchemy/")

    assert response.status_int == 200
    assert response.text == "Hello from the DB!"
    assert len(tracked_requests) == 1
    tracked_request = tracked_requests[0]
    spans = tracked_request.complete_spans
    assert len(spans) == 2
    assert [s.operation for s in spans] == [
        "SQL/Query",
        "Controller/tests.integration.test_flask_sqlalchemy.sqlalchemy",
    ]
    assert spans[0].tags["db.statement"] == "SELECT 'Hello from the DB!'"
