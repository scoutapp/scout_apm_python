Dev Guide
=========

Setup
-----

Install Python. Any version will do.

Create a virtualenv. There are various ways to do this depending on which
Python version you're using and which tools you prefer.
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/) is a good
choice:

    $ mkvirtualenv scout_apm

Install development tools:

    $ pip install black flake8 isort tox

If you want to test the Elasticsearch, MongoDB and Redis integrations, install
these services and set env variables to declare where they're running. If
you're using virtualenvwrapper, you can export them automatically when
activating the virtualenv:

    $ vi $VIRTUAL_ENV/bin/postactivate

    export ELASTICSEARCH_URL="http://localhost:9200/"
    export MONGODB_URL="mongodb://localhost:27017/"
    export REDIS_URL="redis://localhost:6379/0"
    export URLLIB3_URL="http://localhost:9200/"

Re-activate the virtualenv to export the env variables:

    $ workon scout_apm

Checking code quality
---------------------

scout_apm relies on [black](https://black.readthedocs.io/) and
[isort](https://isort.readthedocs.io/) for automated code formatting.

Don't spend a second thinking about code formatting. Just type valid Python
and let the computer do the work for you:

    $ make style

scout_apm also relies on [flake8](https://flake8.readthedocs.io/) to enforce
good Python style, which is known as "linting".

Check for errors with:

    $ make lint

Travis CI enforces these checks.

Running tests
-------------

[tox](https://tox.readthedocs.io/) allows testing easily against various
Python and Django versions.

tox creates a virtualenv and installs dependencies according to the requested
version.

See supported versions:

    $ tox -l

Run tests with selected Python and Django versions (recommended):

    $ tox -e py37-django21

Run tests on all supported combinations (not recommended - this is slow):

    $ tox

Writing a test, creating a pull request and letting Travis CI run `tox` is
usually the most efficient way to confirm that code works across Python and
Django versions.

Running tests quickly
---------------------

If you want to iterate quickly and find tox slow, you can run tests directly
in the virtualenv where you're working.

You can create different virtualenvs to test with different Python versions,
for example 2.7 and 3.7. In that case, do the whole setup for each virtualenv.

Install all test dependencies:

    $ pip install bottle celery Django elasticsearch flask flask-sqlalchemy jinja2 mock psutil pymongo pyramid pytest pytest-travis-fold pytest-cov redis requests sqlalchemy urllib3 webtest

Run tests with:

    $ PYTHONPATH=src pytest

Run tests only for a package or module like this:

    $ PYTHONPATH=src pytest tests/unit/core/test_config.py

Run a single test like this:

    $ PYTHONPATH=src pytest -k test_boolean_conversion_from_env

The source code is in a `src/` subdirectory to prevent importing it
accidentally so you need to add it to `PYTHONPATH` — see details
[here](https://hynek.me/articles/testing-packaging/).

Running the test app
--------------------

Add the following env variables:

    $ vi $VIRTUAL_ENV/bin/postactivate

    export SCOUT_MONITOR="True"
    export SCOUT_KEY="<your Scout APM key>"
    export SCOUT_NAME="Python test"

Re-activate the virtualenv to export the env variables:

    $ workon scout_apm

Run the test app:

    $ PYTHONPATH=. tests/integration/app.py

You can also run it with gunicorn:

    $ pip install gunicorn
    $ gunicorn tests.integration.app:app

Or with waitress:

    $ pip install waitress
    $ waitress-serve tests.integration.app:app

Or with any other WSGI server, really!

As above, you can create different virtualenvs to test with different Python
versions, provided you do the whole setup for each virtualenv.
