# Scout Python APM Agent

[![travis](https://img.shields.io/travis/scoutapp/scout_apm_python/master.svg)](https://travis-ci.org/scoutapp/scout_apm_python)
[![pypi](https://img.shields.io/pypi/v/scout-apm.svg)](https://pypi.python.org/pypi/scout-apm)
[![docs](https://img.shields.io/badge/docs-read%20online-green.svg)](https://docs.scoutapm.com/#python-agent)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Monitor the performance of Python Django apps, Flask apps, and Celery workers with Scout's [Python APM Agent](https://www.scoutapm.com). Detailed performance metrics and transaction traces are collected once the `scout-apm` package is installed and configured.

![screenshot](https://s3-us-west-1.amazonaws.com/scout-blog/python_monitoring_release/python_monitoring_screenshot.png)

## Requirements

Python 2.7 or 3.4+.

Scout APM has integrations for the following frameworks:

* Bottle 0.12+
* Celery 3.1+
* Django 1.8+
* Dramatiq 1.0+
* Falcon 2.0+
* Flask 0.10+
* Huey 2.0+
* Nameko 2.0+
* Pyramid 1.8+
* Starlette 0.12+

For other frameworks, you can use the agent's instrumentation API. See the [Python help docs](https://docs.scoutapm.com/#python-agent) for more information.

## Quick Start

__A Scout account is required. [Signup for Scout](https://scoutapm.com/users/sign_up).__

```sh
pip install scout-apm
```

### Bottle

```python
from scout_apm.bottle import ScoutPlugin

app = bottle.default_app()
app.config.update({
    "scout.name": "YOUR_APP_NAME",
    "scout.key": "YOUR_KEY",
    "scout.monitor": "true",
})

scout = ScoutPlugin()
bottle.install(scout)
```

### Django

```python
# settings.py
INSTALLED_APPS = [
    "scout_apm.django",  # should be listed first
    # ... other apps ...
]

# Scout settings
SCOUT_MONITOR = True
SCOUT_KEY = "[AVAILABLE IN THE SCOUT UI]"
SCOUT_NAME = "A FRIENDLY NAME FOR YOUR APP"
```

### Falcon

```python
import falcon
from scout_apm.falcon import ScoutMiddleware

scout_middleware = ScoutMiddleware(config={
    "key": "[AVAILABLE IN THE SCOUT UI]",
    "monitor": True,
    "name": "A FRIENDLY NAME FOR YOUR APP",
})
api = falcon.API(middleware=[ScoutMiddleware()])
# Required for accessing extra per-request information
scout_middleware.set_api(api)
```

### Flask

These instructions assume the app uses `SQLAlchemy`. If that isn't the case, remove the referencing lines.

```python
from scout_apm.flask import ScoutApm
from scout_apm.flask.sqlalchemy import instrument_sqlalchemy

# Setup a flask 'app' as normal

# Attach ScoutApm to the Flask App
ScoutApm(app)

# Instrument the SQLAlchemy handle
instrument_sqlalchemy(db)

# Scout settings
app.config["SCOUT_MONITOR"] = True
app.config["SCOUT_KEY"] = "[AVAILABLE IN THE SCOUT UI]"
app.config["SCOUT_NAME"] = "A FRIENDLY NAME FOR YOUR APP"
```

### Pyramid

Add the `SCOUT_*` settings to the Pyramid config, and then `config.include('scout_apm.pyramid')`


```python
import scout_apm.pyramid

if __name__ == "__main__":
    with Configurator() as config:
        config.add_settings(
            SCOUT_KEY="...",
            SCOUT_MONITOR=True,
            SCOUT_NAME="My Pyramid App"
        )
        config.include("scout_apm.pyramid")

        # Rest of your config...
```

## Documentation

For full installation instructions, including information on configuring Scout
via environment variables and troubleshooting documentation, see our
[Python docs](https://docs.scoutapm.com/#python-agent).

## Support

Please contact us at support@scoutapm.com or create an issue in this repo.
