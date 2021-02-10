Dev Guide
=========

Basic Setup
-----------

**First**, install one or more of the supported Python versions. It's best to
install all, which can be done with [pyenv](https://github.com/pyenv/pyenv).

**Second**, install [pre-commit](https://pre-commit.com/). This can be done
with your system package manager, such as `brew install pre-commit`.

**Third**, install pre-commit into the local repository:

```
pre-commit install
```

**Fourth**, check your pre-commit is working by running all the checks:

```
pre-commit run --all-files
```

**Fifth**, install [tox](https://tox.readthedocs.io/en/latest/) on your system
Python (it’s best to use the latest version of Python for this):

```
python -m pip install tox
```

**Sixth**, run the tests. tox has many environments defined in the `envlist`
key in `tox.ini`, which you can list with `tox -l`. Pick one for a Python
version that you have installed and run the tests, for example:

```
tox -e py39-django31
```

If you run `tox` with no arguments, it will test all environments. This will
take a while - it's often more efficient to only run all environments on CI.

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

For example, to run `pytest --pdb`, which starts PDB on test failure, run e.g.
`tox -e py39-django31 -- --pdb`.

You can use this to run a specific test file, for example
`tox -e py39-django31 -- tests/integration/test_django.py`.

Test Services
-------------

Some of the tests require external services to run against. These are specified
by environment variables. These are:

* `ELASTICSEARCH_URL` - point to a running Elasticsearch instance, e.g.
  "http://localhost:9200/" . You can start it with:
  `docker run --detach --name elasticsearch --publish 9200:9200 -e "discovery.type=single-node" elasticsearch:7.10.1` .
* `MONGODB_URL` - point to a running MongoDB instance e.g.
  "mongodb://localhost:27017/" . You can start it with:
  `docker run --detach --name mongo --publish 27017:27017 mongo:4.0` .
* `REDIS_URL` - point to a running Redis instance e.g.
  "redis://localhost:6379/0" . You can start it with:
  `docker run --detach --name redis --publish 6379:6379 redis:6` .

You can `export` any of these environment variables and run the respective
tests with `tox`.

Running the test app
--------------------

Note: this has not been tested in a while. Instead, the
[scout-test-apps repo](https://github.com/tim-schilling/scout-test-apps) has
been used with many individual scout apps.

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

Releases
--------

Releases are run in the "releases" GitHub Actions Workflow. This runs on every
pull request and commit to master, to check that the build works. When a tag
is pushed that starts with 'v', the built artifacts will also be uploaded to
PyPI, using a password stored in the GitHub Actions Secrets.

The build process uses the [cibuildwheel
tool](https://cibuildwheel.readthedocs.io/) to handle much of the complexity
of building binary wheels across different Python versions and processor
architectures. Its documentation is excellent.

Documentation
-------------

The user documentation is stored in the [slate_apm_help
repo](https://github.com/scoutapp/slate_apm_help) in the
`source/_includes/python.md` file. Make relevant changes there when developing
features.
