from __future__ import absolute_import, division, print_function, unicode_literals

from celery import Celery

app = Celery("tasks", broker="memory://")


@app.task
def hello():
    return "Hello World!"
