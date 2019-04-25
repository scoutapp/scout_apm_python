# Scout Python APM Agent

Monitor the performance of Python Django apps, Flask apps, and Celery workers with Scout's [Python APM Agent](https://www.scoutapp.com). Detailed performance metrics and transaction traces are collected once the `scout-apm` package is installed and configured.

![screenshot](https://s3-us-west-1.amazonaws.com/scout-blog/python_monitoring_release/python_monitoring_screenshot.png)

## Requirements

Python Versions:

* Python 3.4+
* Python 2.7

Scout APM works with the following frameworks:

* Django 1.8+
* Flask 0.10+
* Celery 3.1+
* Pyramid 1.8+
* Bottle 0.12+

For frameworks not listed above, you can use the agent's instrumentation API. See the [Python help docs](https://docs.scoutapm.com/#python-agent) for more information.

## Quick Start

__A Scout account is required. [Signup for Scout](https://scoutapm.com/users/sign_up).__

```sh
pip install scout-apm
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

For full installation instructions, including information on configuring Scout via environment variables, see our [Python docs](https://docs.scoutapm.com/#python-agent).

## Documentation

For full installation and troubleshooting documentation, visit our
[help site](https://docs.scoutapm.com/#python-agent).

## Support

Please contact us at support@scoutapm.com or create an issue in this repo.
