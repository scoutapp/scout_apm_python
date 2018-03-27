# Scout Python Monitoring Agent

Python Agent for [Scout Application Monitoring](https://www.scoutapp.com).

Python Monitoring is in our Technical Preview Program. If you run into any questions or issues, contact us at support@scoutapp.com or create an issue in this repo.

![screenshot](https://s3-us-west-1.amazonaws.com/scout-blog/python_monitoring_release/python_monitoring_screenshot.png)

## Django Quick Start

```sh
pip install scout-apm
```

```python
# settings.py
INSTALLED_APPS = (
  'scout_apm.django', # should be listed first
  # ... other apps ...
)

# Scout settings
SCOUT_MONITOR = True
SCOUT_KEY     = "[AVAILABLE IN THE SCOUT UI]"
SCOUT_NAME    = "[A FRIENDLY NAME FOR YOUR APP]"
```
For full installation instructions, including information on configuring Scout via environment variables, see our [Python docs](http://help.apm.scoutapp.com/#python-agent).

## Documentation

For full installation and troubleshooting documentation, visit our
[help site](http://help.apm.scoutapp.com/#python-agent).


