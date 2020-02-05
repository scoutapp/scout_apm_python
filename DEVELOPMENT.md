Dev Guide
=========

Basic Setup
-----------

**First,** install one or more of the supported Python versions. It's best to
install all which can be done with [pyenv](https://github.com/pyenv/pyenv).

**Second,** install [tox](https://tox.readthedocs.io/en/latest/) with
`python -m pip install tox`. Best to use the latest version of Python you have
installed for this.

**Third,** run the tests with a tox environment. For example,
`tox -e py37-django22` will run with Python 3.7 and Django 2.2.

You can get a list of all the defined environments with `tox -l`. They're
defined at the top of `tox.ini`.

If you run `tox` with no arguments, it will test all environments. There are a
lot of environments so this can take some time. It's best to only let CI do
this when you create a pull request.

**Fourth,** run the code style checks with `tox -e check`. Everything should
pass.

**Fifth,** install the pre-commit code style checks hook with
`.tox/check/bin/pre-commit install`. This will use
[pre-commit](https://pre-commit.com/) inside the virtual environment that tox
made to run the checks every time you commit.

Editable Mode
-------------

If you want to test an application with the development version of Scout, you
can install it in "editable mode" in that application's virtual environment.
Use `pip install -e path/to/scout_apm_python` to do this. This makes the
virtual environment import scout from the repository directly so you can edit
it to test changes.

Running Tests
-------------

Tox runs the tests with [pytest](https://docs.pytest.org/en/latest/). You can
pass arguments through to Pytest after a `--` to signify the end of arguments
for tox to parse.

For example, to run `pytest --pdb`, which starts PDB on test failure, run
`tox -e py37-django22 -- --pdb`.

You can use this to run a specific test file, for example
`tox -e py37-django22 -- tests/integration/test_django.py`.

Test Services
-------------

Some of the tests require external services to run against. These are specified
by environment variables. These are:

* `ELASTICSEARCH_URL` - point to a running Elasticsearch instance, e.g.
  "http://localhost:9200/" . You can start it with:
  `docker run --detach --name elasticsearch --publish 9200:9200 -e "discovery.type=single-node" elasticsearch:7.5.2` .
* `MONGODB_URL` - point to a running MongoDB instance e.g.
  "mongodb://localhost:27017/" . You can start it with:
  `docker run --detach --name mongo --publish 27017:27017 mongo:4.0` .
* `REDIS_URL` - point to a running Redis instance e.g.
  "redis://localhost:6379/0" . You can start it with:
  `docker run --detach --name redis --publish 6379:6379 redis:5` .

You can `export` any of these environment variables and run the respective
tests with `tox`.

Running the test app
--------------------

Add the following env variables:

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
