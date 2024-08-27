# Scout Python APM Agent

[![GitHub Actions](https://github.com/scoutapp/scout_apm_python/workflows/CI/badge.svg?branch=master)](https://github.com/scoutapp/scout_apm_python/actions?workflow=CI)
[![PyPI](https://img.shields.io/pypi/v/scout-apm.svg)](https://pypi.python.org/pypi/scout-apm)
[![Documentation](https://img.shields.io/badge/docs-read%20online-green.svg)](https://docs.scoutapm.com/#python-agent)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Monitor the performance of Python Django apps, Flask apps, and Celery workers with Scout's [Python APM Agent](https://www.scoutapm.com). Detailed performance metrics and transaction traces are collected once the `scout-apm` package is installed and configured.

## Requirements

Python 3.8+.
For legacy Python versions, including 2.7 and 3.4+, pin scout-apm to <=2.26.1.

Scout APM has integrations for the following frameworks:

* Bottle 0.12+
* Celery 3.1+
* Django 3.2+
* Dramatiq 1.0+
* Falcon 2.0+
* Flask 0.10+
* Huey 2.0+
* Hug 2.5.1+
* RQ 1.0+
* Starlette 0.12+

For other frameworks, you can use the agent's instrumentation API.

To use Scout, you'll need to
[sign up for an account](https://scoutapm.com/users/sign_up) or use
[our Heroku Addon](https://devcenter.heroku.com/articles/scout).

## Documentation

For full installation instructions, including information on configuring Scout
via environment variables and troubleshooting, see our
[Python docs](https://scoutapm.com/docs/python).

## Support

Please email us at support@scoutapm.com or [create a GitHub
issue](https://github.com/scoutapp/scout_apm_python/issues/).
