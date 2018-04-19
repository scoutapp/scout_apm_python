_Python Monitoring is in our Technical Preview Program. If you run have questions or run into issues, contact us at support@scoutapp.com or create an issue in this repo._

# Scout Python Monitoring Agent

This is the Python Agent for [Scout Application Monitoring](https://www.scoutapp.com). Install this agent in your Python application to collect detailed performance metrics and transaction traces. Data is reported to Scout.

![screenshot](https://s3-us-west-1.amazonaws.com/scout-blog/python_monitoring_release/python_monitoring_screenshot.png)

## Quick Start

__A Scout account is required. [Signup for Scout](https://apm.scoutapp.com/users/sign_up).__

```sh
pip install scout-apm
```

### Django

```python
# settings.py
INSTALLED_APPS = (
  'scout_apm.django', # should be listed first
  # ... other apps ...
)

# Scout settings
SCOUT_MONITOR = True
SCOUT_KEY     = "[AVAILABLE IN THE SCOUT UI]"
SCOUT_NAME    = "A FRIENDLY NAME FOR YOUR APP"
```

### Flask

These instructions assume the app uses `SQLAlchemy`. If that isn't the case, remove the referencing lines.

```python
from scout_apm.flask import ScoutApm
from scout_apm.flask.sqlalchemy import instrument_sqlalchemy

# Setup a flask 'app' as normal

## Attaches ScoutApm to the Flask App
ScoutApm(app)

## Instrument the SQLAlchemy handle
instrument_sqlalchemy(db)

# Scout settings
app.config['SCOUT_MONITOR'] = True
app.config['SCOUT_KEY']     = "[AVAILABLE IN THE SCOUT UI]"
app.config['SCOUT_NAME']    = "A FRIENDLY NAME FOR YOUR APP"
```

For full installation instructions, including information on configuring Scout via environment variables, see our [Python docs](http://help.apm.scoutapp.com/#python-agent).

## Documentation

For full installation and troubleshooting documentation, visit our
[help site](http://help.apm.scoutapp.com/#python-agent).


