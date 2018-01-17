Scout APM Python Agent
======================

Python agent for [Scout Application Monitoring](https://www.scoutapp.com).

This is early in development, and is not usable. If you have any questions, contact us at
support@scoutapp.com.

Installation
============

* Symlink the apm/ dir into your django app.
* `import apm` at the top of settings.py
* In settings.py, Add a middleware: 'apm.middleware.LogTimesMiddleware'
* In settings.py, Add a key to TEMPLATES = [ { 'OPTIONS': { 'builtins': ['apm.instruments.template'] } } ]


