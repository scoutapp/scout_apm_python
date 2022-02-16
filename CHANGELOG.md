# Changelog

## Pending

### Added

### Fixed

## [2.24.1] 2022-02-16

### Added
- Add `log_payload_content` to support logging the content of the message
  being sent to either the core agent socket or the error service.
  ([Issue 724](https://github.com/scoutapp/scout_apm_python/issues/724))

### Fixed

## [2.24.0] 2022-02-08

### Fixed
- Only log warnings for ElasticSearch client method instrumentation
  if no client methods were instrumented. Otherwise, log the issues at
  the debug level. This avoids flooding logs when clients use an older
  version of ElasticSearch.
  ([Issue 713](https://github.com/scoutapp/scout_apm_python/issues/713))
- Restore building wheels for python 3.4 and 3.5.
  ([Issue 584](https://github.com/scoutapp/scout_apm_python/issues/584))

## [2.23.5] 2021-12-09

### Added

### Fixed
- Avoid instrumenting PyMongo collection methods that were removed in v4.
  ([Issue 710](https://github.com/scoutapp/scout_apm_python/issues/710))
- When Celery `task_failure` signal has a string type for the `traceback`
  parameter, use the `einfo.tb` to fetch the traceback.
  ([Issue 708](https://github.com/scoutapp/scout_apm_python/issues/708))
- Use urllib3 to post errors to Scout Errors API. Removes dependency on
  requests library.
- Switch to a dict for the `request_params` away from a list of tuples.

## [2.23.4] 2021-11-12

### Added
- Split CI tests GitHub actions into two jobs to support python 3.4 on
  Ubuntu 18 and modern versions with Ubuntu 20.
- Run CI tests once per day to identify issues quicker.
- Set Scout core agent default version to v1.4.0.
  ([Issue 700](https://github.com/scoutapp/scout_apm_python/issues/700))
- Instrument Flask for Error Monitoring.

### Fixed
- Properly handle querystring parameters in error monitoring service by
  passing them as a list of tuples rather than a dictionary. When there
  were multiple params with the same key, it was keeping the last value.

## [2.23.3] 2021-11-04

### Added
- Added support for Django 4.0 and Python 3.10.

### Fixed
- Make `module_filepath` more robust avoiding throwing exceptions.
  ([Issue 691](https://github.com/scoutapp/scout_apm_python/issues/691))

## [2.23.2] 2021-10-04

### Added
- Reverted - Rework release Github action to utilize newer versions of cibuildwheel when available.

## [2.23.1] 2021-10-04

### Added
- Rework release Github action to utilize newer versions of cibuildwheel when available.
- Added `search_mvt` instrumentation for ElasticSearch 7.15.0.
- Default core agent version to v1.3.1. Support ARM64 core agent architecture.
  ([Issue #683](https://github.com/scoutapp/scout_apm_python/issues/683))


## [2.23.0] 2021-09-06

### Added
- Convert objtrace to use PEP 489 multi-phase initialization.
  ([Issue #661](https://github.com/scoutapp/scout_apm_python/issues/661))
- Enable error monitoring by default.

### Fixed
- Disconnect receiver from celery task_failure signal.
  ([Issue #678](https://github.com/scoutapp/scout_apm_python/issues/678))


## [2.22.1] 2021-08-19

### Added
- Prevent a TrackedRequest from being sent more than once. Additional
  logging was added to identify cases when this is occurring.

### Fixed
- Define TrackedRequest ContextVar at module level and ignore tokens.
  ([Issue #675](https://github.com/scoutapp/scout_apm_python/issues/675))


## [2.22.0] 2021-08-12

### Added
- Added `terms_enum` instrumentation for ElasticSearch 7.14.0.
  ([Issue #671](https://github.com/scoutapp/scout_apm_python/issues/671))

### Fixed
- Switch to storing TrackedRequest in a ContextVar for Python3.6+ rather than in a thread local.
- Support instrumenting Jinja v3 ``render_async`` function.
  ([Issue #646](https://github.com/scoutapp/scout_apm_python/issues/646))

## [2.21.1] 2021-07-27

### Fixed
- Handle case of namespace packages when capturing backtraces.
  ([Issue #667](https://github.com/scoutapp/scout_apm_python/issues/667))

## [2.21.0] 2021-07-23

### Added
- Support Error Monitoring. See
  [integration docs](https://scoutapm.com/docs/python/error-monitoring).
  ([PR #651](https://github.com/scoutapp/scout_apm_python/pull/651))
- Deprecate `backtrace.capture` in favor of `backtrace.capture_backtrace`

### Fixed
- Setup metadata keywords now contains an array of strings.
- Remove non-project paths from traces.
  ([Issue #416](https://github.com/scoutapp/scout_apm_python/issues/416))


## [2.20.0] 2021-07-21
- Removed parsing queue time from Amazon ALB header, X-Amzn-Trace-Id.
  The time portion of the header only has the truncated seconds which
  appears as about 500ms for queue time constantly.
  ([Issue #631](https://github.com/scoutapp/scout_apm_python/issues/631))
- Added Celery's ``priority`` delivery info to the set of tags.
- Changed max spans reached log level from warning to debug.
  ([Issue #653](https://github.com/scoutapp/scout_apm_python/issues/653))
- Improved debug logging for requests. It now includes some summary
  information about the request.
  ([Issue #654](https://github.com/scoutapp/scout_apm_python/issues/654))
- Set ``TrackedRequest.tags("error", "true")`` when Celery tasks fail.
  ([Issue #649](https://github.com/scoutapp/scout_apm_python/issues/649))

## [2.19.0] 2021-05-04

### Added

- Tested with Django 3.2. Only define ``default_app_config`` when using
  a version of Django earlier than 3.2.
- Support instrumentation and transaction decorators for asynchronous
  functions via ``@instrument.async_``, ``@WebTransaction.async_`` and
  ``@BackgroundTransaction.async_``.
  ([PR #633](https://github.com/scoutapp/scout_apm_python/issues/633))

### Fixed

- Exclude python library paths from backtraces.
  ([PR #514](https://github.com/scoutapp/scout_apm_python/issues/514))
- Preserve tracked request across asyncio tasks.
  ([PR #469](https://github.com/scoutapp/scout_apm_python/issues/469))

## [2.18.0] 2021-02-09

### Added

- Instrument new Elasticsearch methods `close_point_in_time()` and
  `open_point_in_time()`.
  ([PR #602](https://github.com/scoutapp/scout_apm_python/pull/602))

- The release now includes binary wheels for Linux ARM and Python 3.9.

### Fixed

- Support hex timestamp in Amazon headers
  ([PR #598](https://github.com/scoutapp/scout_apm_python/pull/598))
- Fix a socket resource leak when downloading the core agent.
  ([PR #609](https://github.com/scoutapp/scout_apm_python/pull/609))
- Fix Starlette with ASGI apps that are class instances
  ([Issue #596](https://github.com/scoutapp/scout_apm_python/issues/596))

## [2.17.0] 2020-09-17

### Added

- Support Python 3.9.
  ([PR #583](https://github.com/scoutapp/scout_apm_python/pull/583))

## [2.16.2] 2020-09-17

- Moved core agent on Linux to default to the musl version, rather than try
  detect whether to use the musl or GNU libc version.
  ([PR #585](https://github.com/scoutapp/scout_apm_python/pull/585))

## [2.16.1] 2020-09-09

### Fixed

- Added a cast to string of query parameters, to work around cases where
  application code changes them to non-strings. Fixes a possible exception:
  `AttributeError: 'int' object has no attribute 'encode'` in
  `scout.core.web_requests`.

## [2.16.0] 2020-09-08

### Added

- Changed default agent connection to use TCP rather than a unix socket. By
  default the agent will be run on 127.0.0.1, port 6590. This should resolve
  a number of connection issues. To continue using a socket connection,
  [configure
  `core_agent_socket_path`](https://docs.scoutapm.com/#python-configuration).
  ([Issue #553](https://github.com/scoutapp/scout_apm_python/issues/553))
- Tested with Django 3.1. No compatibility changes were required, but this is
  the first release to be tagged as supporting it.

### Fixed

- Fixed validation check on length of key.
  ([Issue #563](https://github.com/scoutapp/scout_apm_python/issues/563))
- Update Core Agent to version 1.3.0, fixing several bugs and opening the
  ability to run with only a TCP socket.
  ([Issue #567](https://github.com/scoutapp/scout_apm_python/issues/567))

## [2.15.2] 2020-07-24

### Fixed

- On Django, only track the current user ID if `request.user` was accessed by
  application code. This stops a `Vary: Cookie` header being injected due to
  session data access.
  ([Issue #544](https://github.com/scoutapp/scout_apm_python/issues/544))

## [2.15.1] 2020-07-23

### Fixed

- Always convert `collect_remote_ip` to boolean.
  ([Issue #542](https://github.com/scoutapp/scout_apm_python/issues/542))

## [2.15.0] 2020-07-22

### Added

- Extended RQ integration with `HerokuWorker` class for use in the RQ Heroku
  pattern.
  ([Issue #529](https://github.com/scoutapp/scout_apm_python/issues/529))
- Added the `collect_remote_ip` / `SCOUT_COLLECT_REMOTE_IP` setting which can
  be set to `False` to disable storing user IP addresses in Scout traces.
  ([Issue #535](https://github.com/scoutapp/scout_apm_python/issues/535))

## [2.14.3] 2020-06-05

### Fixed

- Don't log the Scout key during startup.
  ([Issue #297](https://github.com/scoutapp/scout_apm_python/issues/297))

## [2.14.2] 2020-05-22

### Fixed

- Fix crash when scanning packages that have a Name or Version that is
  `None`.
  ([Issue #522](https://github.com/scoutapp/scout_apm_python/issues/522))

## [2.14.1] 2020-04-28

### Fixed

- Update Core Agent to version 1.2.9, fixing several bugs.
  ([Issue #516](https://github.com/scoutapp/scout_apm_python/issues/516))

## [2.14.0] 2020-04-08

### Fixed

- Support Django's `BASE_DIR` setting being a `pathlib.Path`, as the default
  template in Django 3.1 will set.
  ([Issue #503](https://github.com/scoutapp/scout_apm_python/pull/503))
- Instrument new Elasticsearch methods `get_script_context()` and
  `get_script_languages()`.
  ([PR #507](https://github.com/scoutapp/scout_apm_python/pull/507))
- Prevent output from the core agent when starting it.
  ([Issue #510](https://github.com/scoutapp/scout_apm_python/issues/510))

## [2.13.0] 2020-03-09

### Added

- Added config value `shutdown_message_enabled` /
  `SCOUT_SHUTDOWN_MESSAGE_ENABLED` which can be set to "false" to disable the
  shutdown message "Scout draining N events..."that was added in version
  2.11.0.
  ([Issue #498](https://github.com/scoutapp/scout_apm_python/issues/498))
- Renamed `config_file`, `log_file`, and `socket_path` to have the
  `core_agent_` prefix. This is to clarify that they apply only to the core
  agent process. The old names continue to work as aliases.
  ([Issue #497](https://github.com/scoutapp/scout_apm_python/issues/497))
- Improved some log messages and levels around instrumentation.
  ([Issue #502](https://github.com/scoutapp/scout_apm_python/pull/502))

## [2.12.0] 2020-03-03

### Added

- Added ability to read configuration from your Celery app. This can help share
  configuration between Django and Celery. Pass your application as `app` to
  have the configuration copied: `scout_apm.celery.install(app=app)` .
  ([Issue #477](https://github.com/scoutapp/scout_apm_python/issues/477))
- Added maximum span limit of 1500. This prevents memory exhaustion when
  tracing long running tasks as Scout no longer tries to record everything.
  ([Issue #472](https://github.com/scoutapp/scout_apm_python/issues/472))

### Fixed

- Made installation of the objtrace C extension optional, so that if it fails
  due to your C compiler being old, Scout can still install.
  ([Issue #488](https://github.com/scoutapp/scout_apm_python/issues/488))
- Removed warning for setting the `SCOUT_LOG_LEVEL` setting, since this is set
  by default by the Heroku add-on.
  ([Issue #486](https://github.com/scoutapp/scout_apm_python/issues/486]))

## [2.11.0] 2020-02-17

### Added

- Improve Falcon integration: tracing is automatically disabled if
  installation fails, track middleware, and support class-based responders.
  ([PR #453](https://github.com/scoutapp/scout_apm_python/pull/453),
  [PR #460](https://github.com/scoutapp/scout_apm_python/pull/460))
- Add Hug integration.
  ([PR #460](https://github.com/scoutapp/scout_apm_python/pull/460))
- Limit size of recorded tracebacks to reduce memory usage.
  ([PR #476](https://github.com/scoutapp/scout_apm_python/pull/476))
- Scout now flushes any queued commands to the core agent at shutdown, with a
  configurable timeout `shutdown_timeout_seconds`, defaulting to 2 seconds.
  This ensures that all traces are recorded, rather than lost, especially
  useful for single-run background commands.
  ([Issue # 473](https://github.com/scoutapp/scout_apm_python/issues/473))
- Move from **requests** to underlying **urllib3** for downloads to reduce
  dependency footprint.
  ([PR #480](https://github.com/scoutapp/scout_apm_python/pull/480))
- Retry downloading the core agent a few times, and use a timeout to prevent
  startup hangs.
  ([PR #480](https://github.com/scoutapp/scout_apm_python/pull/480))

### Fixed

- Moved some user-facing warnings, such as for deprecated features, from
  `logging` to `warnings`, so they can be caught during testing.
  ([PR #468](https://github.com/scoutapp/scout_apm_python/pull/468))
- Fix Jinja2 asynchronous rendering instrumentation for Jinja2 2.11.0+.
  ([PR #462](https://github.com/scoutapp/scout_apm_python/pull/462))
- Stop patching `elasticsearch`'s `scripts_painless_context()`, because it has
  been removed in version 7.5.1.
  ([Issue #454](https://github.com/scoutapp/scout_apm_python/issues/454))
- Fix for `elasticsearch` version 7.5.1's change of positional argument order.
  ([Issue #456](https://github.com/scoutapp/scout_apm_python/issues/456))

## [2.10.0] 2020-01-02

### Added

- Use Python 3.8's standard library `importlib.metadata.distributions()` to
  determine package versions, rather than `pkg_resources`. The [backport
  package
  `importlib_metadata`](https://pypi.org/project/importlib-metadata/) is
  required on older Python versions.
  ([PR #430](https://github.com/scoutapp/scout_apm_python/pull/430))
- Add CherryPy integration.
  ([PR #431](https://github.com/scoutapp/scout_apm_python/pull/431))
- Add tracking for missing PyMongo Collection methods.
  ([PR #436](https://github.com/scoutapp/scout_apm_python/pull/436))
- Add tracking for missing Elasticsearch client methods.
  ([PR #438](https://github.com/scoutapp/scout_apm_python/pull/438))

### Removed

- Remove the "name" context tag from Flask requests - it only duplicated the
  request name.
  ([PR #432](https://github.com/scoutapp/scout_apm_python/pull/432))

## [2.9.1] 2019-12-13

### Added

- Update Core Agent to version 1.2.6, fixing several bugs:
    - Improve SQL statement names in Timeline Traces
    - Standardize on a `language_version` key in metadata
    - Autoclose spans that are still running when a Request completes

  ([PR #415](https://github.com/scoutapp/scout_apm_python/pull/415))

### Fixed

- Fix recording of path for unicode query parameters on Python 2.7.
  ([PR #419](https://github.com/scoutapp/scout_apm_python/pull/419))

## [2.9.0] 2019-11-30

### Added

- Add RQ integration.
  ([PR #375](https://github.com/scoutapp/scout_apm_python/pull/375))
- Track 5XX responses as errors from all web frameworks.
  ([Issue #383](https://github.com/scoutapp/scout_apm_python/issues/383))
- Track Flask's request preprocessors as a span `PreprocessRequest`.
  ([PR #390](https://github.com/scoutapp/scout_apm_python/pull/390))
- Track Jinja2 asynchronous template rendering.
  ([PR #398](https://github.com/scoutapp/scout_apm_python/pull/398))
- Add Django-Huey integration.
  ([PR #401](https://github.com/scoutapp/scout_apm_python/pull/401))

### Fixed

- Track better names for Django REST Framework `ViewSet`s.
  ([PR #380](https://github.com/scoutapp/scout_apm_python/pull/380))
- Always capture SQL tracebacks for `executemany` queries going over the
  built-in count threshold.
  ([PR #409](https://github.com/scoutapp/scout_apm_python/pull/409))
- Don't capture internal traceback function's frame in tracebacks.
  ([PR #410](https://github.com/scoutapp/scout_apm_python/pull/410))

## [2.8.1] 2019-11-19

### Fixed

- Fixed memory allocation tracking, which has been broken since a refactor in
  version 2.7.0.

## [2.8.0] 2019-11-08

### Added

- Move all decorators to the [`wrapt`
  library](https://wrapt.readthedocs.io/en/latest/) which is more transparent.
  ([PR #324](https://github.com/scoutapp/scout_apm_python/pull/324))
- Move context tracking to be async-compatble with `asgiref`'s `Local`.
  ([PR #349](https://github.com/scoutapp/scout_apm_python/pull/349))
- Add Starlette integration for Python 3.6+.
  ([PR #349](https://github.com/scoutapp/scout_apm_python/pull/349))
- Add Huey integration.
  ([PR #367](https://github.com/scoutapp/scout_apm_python/pull/367))

### Fixed

- Track SQL Alchemy `executemany` calls as multi-queries.
  ([PR #340](https://github.com/scoutapp/scout_apm_python/pull/340))
- Track Elasticsearch index name when it's not passed as a keyword argument.
  ([PR #348](https://github.com/scoutapp/scout_apm_python/pull/348))
- Increase core agent socket timeout to reduce reconnections.
  ([PR #247](https://github.com/scoutapp/scout_apm_python/pull/247))
- Fix the `RemovedInDjango20Warning` for `django.core.urlresolvers` on Django
  1.11. ([PR #359](https://github.com/scoutapp/scout_apm_python/pull/359))
- Correctly disable Bottle if the agent fails to launch.
  ([PR #364](https://github.com/scoutapp/scout_apm_python/pull/364))

## [2.7.0] 2019-11-03

### Added

- Python 3.8 testing and PyPI trove classifier - no code changes were required
  so older versions should work too.
  ([PR #263](https://github.com/scoutapp/scout_apm_python/pull/263))
- Capture better operation names for Django Tastypie resources, e.g.
  `myapp.api.UserResource.get_list`.
  ([PR #332](https://github.com/scoutapp/scout_apm_python/pull/332))

### Fixed

- Change `scout_apm.api.install()` signature to not take `*args, **kwargs` but
  just `config` as a keyword argument.
  ([PR #304](https://github.com/scoutapp/scout_apm_python/pull/304))
- Rewrite background samplers thread to avoid some rare race conditions.
  ([PR #307](https://github.com/scoutapp/scout_apm_python/pull/307))

## [2.6.1] 2019-10-23

### Fixed

- Fix warning emitted from using deprecated 'warn' method
  ([PR #283](https://github.com/scoutapp/scout_apm_python/pull/283)).
- Improve warning message for deprecated `log_level` configuration option
  ([PR #288](https://github.com/scoutapp/scout_apm_python/pull/288)).
- Track errors on Pyramid
  ([PR #298](https://github.com/scoutapp/scout_apm_python/pull/298)).
- Don't start on Windows which is currently not supported
  (request support on [Issue #101](https://github.com/scoutapp/scout_apm_python/issues/101))
  ([PR #299](https://github.com/scoutapp/scout_apm_python/pull/299)).

## [2.6.0] 2019-10-22

### Deprecated

- The `log_level` configuration option is deprecated. Please use the new name
  `core_agent_log_level` instead
  ([PR #273](https://github.com/scoutapp/scout_apm_python/pull/273)).

### Added

- Change default "path" tag on web requests to capture query parameters as
  well. This can be disabled by setting the config value `uri_reporting` to
  `"path"`
  ([PR #268](https://github.com/scoutapp/scout_apm_python/pull/268),
  [PR #269](https://github.com/scoutapp/scout_apm_python/pull/269)).
- Track the `urlconf` on Django, for multi-domain support
  ([PR #276](https://github.com/scoutapp/scout_apm_python/pull/276)).
- Track request queue time from the `X-Amzn-Trace-Id` header, which is [sent by
  AWS ALB's](https://docs.aws.amazon.com/en_pv/elasticloadbalancing/latest/application/load-balancer-request-tracing.html)
  ([PR #279](https://github.com/scoutapp/scout_apm_python/pull/279)).
- Updated Core Agent version to 1.2.4 to support new features
  ([PR #280](https://github.com/scoutapp/scout_apm_python/pull/280)).

### Fixed

- Fix Bottle path tagging to use path from URL rather than controller name
  ([PR #267](https://github.com/scoutapp/scout_apm_python/pull/267)).

## [2.5.0] 2019-09-17

### Added

- Support the `hostname` setting
  ([PR #251](https://github.com/scoutapp/scout_apm_python/pull/251)).
- Support timeline trace view
  ([PR #252](https://github.com/scoutapp/scout_apm_python/pull/252)).
- Add API function `rename_transaction()`
  ([PR #129](https://github.com/scoutapp/scout_apm_python/pull/129)).
- Updated Core Agent version to 1.2.0 to support new features
  ([PR #253](https://github.com/scoutapp/scout_apm_python/pull/253)).

### Fixed

- Use the same default socket name that the core agent uses when launched alone
  (`core-agent.sock` -> `scout-agent.sock`)
  ([PR #240](https://github.com/scoutapp/scout_apm_python/pull/240)).
- Fix CPU statistics to work when the CPU count cannot be determined
  ([PR #245](https://github.com/scoutapp/scout_apm_python/pull/245)).

## [2.4.1] 2019-08-26

### Added

- Improved logging for debugging customer problems
  ([PR #234](https://github.com/scoutapp/scout_apm_python/pull/234)).

### Fixed

- Fixed Flask to not monitor requests when `SCOUT_MONITOR` is set to `False`
  ([PR #235](https://github.com/scoutapp/scout_apm_python/pull/235)).
- Fixed Django to stop monitoring requests when `SCOUT_MONITOR` is set to
  `False` during runtime
  ([PR #236](https://github.com/scoutapp/scout_apm_python/pull/236)).

## [2.4.0] 2019-08-20

### Added

- Add Dramatiq integration
  ([PR #223](https://github.com/scoutapp/scout_apm_python/pull/223)).
- Add Nameko integration
  ([PR #212](https://github.com/scoutapp/scout_apm_python/pull/212)).
- Track Celery task `is_eager`, `exchange`, `routing_key` and `queue` tags
  ([PR #205](https://github.com/scoutapp/scout_apm_python/pull/205)).
- Track Celery task time in queue with context tag `queue_time`
  ([PR #206](https://github.com/scoutapp/scout_apm_python/pull/206)).
- Track Celery task ID with context tag `task_id`, and parent task's ID (for
  chains, chords, etc.) with context tag `parent_task_id`
  ([PR #227](https://github.com/scoutapp/scout_apm_python/pull/227)).
- Improve Django admin views' traced names. Before all admin classes' traces
  would be merged by function name such as
  `django.contrib.admin.options.changelist_view`. Now traces appear per admin
  class, for example `django.contrib.auth.admin.UserAdmin.changelist_view`
  ([PR #226](https://github.com/scoutapp/scout_apm_python/pull/226)).

### Fixed

- Updated Core Agent version to 1.1.11. This fixes the `scm_subdirectory`
  configuration option.

## [2.3.0] 2019-08-04

### Added

- Use Django's native DB instrumentation on Django 2.0+, rather than monkey
  patching the database cursor.
  ([PR #218](https://github.com/scoutapp/scout_apm_python/pull/218)).

### Fixed

- Fix tracking of path on Flask.
  ([PR #221](https://github.com/scoutapp/scout_apm_python/pull/221)).

## [2.2.1] 2019-08-03

### Fixed

- Close file descriptors when launching the core agent process. This fixes a
  bug where uwsgi's HTTP ports would be held by the it on Python 2.7.
  ([PR #219](https://github.com/scoutapp/scout_apm_python/pull/219)).

## [2.2.0] 2019-07-27

### Added

- Track user IP on Flask
  ([PR #190](https://github.com/scoutapp/scout_apm_python/pull/190)).
- Make user IP tracking on Bottle and Pyramid use the same algorithm as other
  integrations, checking for the `client-ip` header
  ([PR #192](https://github.com/scoutapp/scout_apm_python/pull/192),
  [PR #195](https://github.com/scoutapp/scout_apm_python/pull/195)).
- Add support to Bottle, Falcon, Flask and Pyramid integrations for tracking
  request queue timing
  ([PR #199](https://github.com/scoutapp/scout_apm_python/pull/199),
  [PR #201](https://github.com/scoutapp/scout_apm_python/pull/201)).

### Fixed

- Track path and user IP on Django < 1.10
  ([PR #190](https://github.com/scoutapp/scout_apm_python/pull/190)).
- Fix the undocumented `core-agent-manager` CLI command
  ([PR #202](https://github.com/scoutapp/scout_apm_python/pull/202)).
- Consistently track view responses on Django between different versions
  ([PR #203](https://github.com/scoutapp/scout_apm_python/pull/203)).
- Avoid unbalanced request tracking in certain cases on Django < 1.10
  ([PR #203](https://github.com/scoutapp/scout_apm_python/pull/203)).
- Clarified contents of public API by moving some stuff out of it and setting
  `scout_apm.api.__all__`
  ([PR #204](https://github.com/scoutapp/scout_apm_python/pull/204)).

## [2.1.0] 2019-06-25

### Added

- Add support to Django integration for tracking request queue timing from the
  value of the `X-Queue-Start` or `X-Request-Start` header
- Add Falcon integration

## [2.0.5] 2019-06-21

### Added

- Tested on Django 2.2
- Added PyPI Trove classifiers for frameworks
- Track usernames on Django < 1.10

### Fixed

- Stop warnings from using deprecated method `logger.warn`
- Track some missed requests on Flask such as automatic `OPTIONS` responses

## [2.0.4] 2019-04-18

### Fixed

- Fix 'ignore' functionality on Django < 1.10

## [2.0.3] 2019-04-10

### Added

- Add 'scm_subdirectory' config option (PR #155)

### Fixed

- Fixed Elasticsearch integration for queries passing 'index' to `elasticsearch-py` as a list (PR #156)
- Fixes "Registering with app" log message not using configured logger (PR #154)

## [2.0.2] 2019-02-11

### Added

- Add platform triple to config (PR #151)

## [2.0.1] 2019-01-07

### Added

- Adds `core_agent_permissions` configuration option. (PR #147)

### Fixed

- Remove unused dependency on PyYAML (PR #146)

## [2.0.0] 2018-12-18

### Added

- Python 2.7 support
- Ability to 'ignore' requests via configuration option and `scout_apm.api` (PR #144)

## [1.3.8] 2018-09-28

### Added

- Updated Core Agent version to support Database Addon

## [1.3.7] 2018-09-07

### Fixed

- Multi threading lock fix in ThreadLocalSingleton (#127)

## [1.3.6] 2018-09-07

### Fixed

- Update Core Agent

## [1.3.5] 2018-09-06

### Added

- Enable Memory Bloat and Allocation tracking.

### Fixed

- More reliable socket communication with Core Agent (#126)

## [1.3.4] 2018-08-28

### Fixed

- settings.BASE_DIR is optional in Django (#123)

## [1.3.3] 2018-08-27

### Fixed

- Fix issue when `MIDDLEWARE` and `MIDDLEWARE_CLASSES`
  are both defined in Django 1.x apps (PR #122)

## [1.3.2] 2018-08-24

### Fixed

- Fix issue detecting `MIDDLEWARE_CLASSES` in Django apps (#119)

## [1.3.1] 2018-08-22

- Packaging changes only

## [1.3.0] 2018-08-20

### Added

- Track object allocations for every span (Objtrace module)
- Track RSS increase during a TrackedRequest.

### Fixed

- Compatibility with old style Django middleware/settings

## [1.2.3] 2018-08-15

### Added

- Alpine Linux support (Musl based distro) (#108, PR #110)

### Fixed

- Configuration not integrated into derived values (#112)
- Flask Instruments: init_app captures app variable (#104)


## [1.2.2] 2018-07-30

### Fixed

- Look up 'user_ip' context from request headers (PR #90)
- Improved locking/sync around CoreAgentSocket (#91)
- DO not collect backtraces on Controller or Middleware layers (#88)
- Better Elasticsearch naming (#84)
- Flask transactions that throw exceptions don't appear (#29)

## [1.2.1] 2018-07-20

### Added

- Log configuration options to DEBUG on install
- Add Context, Config, and install() to scout_apm.api

### Fixed

- Instrumentation API marks TrackedRequest as real request
- Spans can ignore children (#85)

## [1.2.0] 2018-07-17

### Added

- Determine Application Root
- Deploy Detection
- Additional Instruments:
  - PyMongo
  - UrlLib3
  - Redis
  - Elasticsearch
  - Jinja2
- Instrumentation API

## [1.1.10] 2018-07-11

- Python 3.7 compatibility.

### Fixed

- Python 3.7 makes 'async' a reserved word.

## [1.1.9] 2018-07-09

- Remove python 2.7 from supported versions in setup.py while we work
  to ensure 2.7 compatibility.

### Fixed

- Typo in sqlalchemy for NPlusOneCallSet capture (#73)
- Tuple as logging argument for tagging logger (#74)

## [1.1.8] 2018-06-27

### Added

- Pyramid Support (#58)
- Bottle Support (#64)
- Deploy Tracking Support (#65)
- N+1 Backtrace Capture (#62)

### Fixed

- A few fixes for 2.7 support

## [1.1.7] 2018-06-12

### Added

- Custom instrumentation with a Context Manager or Decorator (#50)
- Enhanced Test Coverage (#53)

### Fixed

- In error conditions that cause unfinished spans, don't raise exceptions (#52)
- Several Python 2.7 Incompatibilities (#56, #57)

###

## [1.1.6] 2018-06-05

### Fixed

- Handle Flask OPTIONS requests (#41)
- Fix incorrect default argument to cursor.execute (#42)
- Remove debugging message for spans that could raise an error

## [1.1.5] 2018-05-25

### Fixed

- Prevent span mismatch from raising on `stop_span`

## [1.1.4] 2018-05-24

### Fixed

- Log INFO message if SCOUT_MONITOR is false
- Except OSError instead of ConnectionRefusedError (python 2.7 compatibility)
- Fix CLI command module import

## [1.1.3] 2018-05-21

### Added

- Basic Celery support
- Capture Tracebacks on spans over 500ms

### Fixed

- Register as Python with APM (previously was not noted explicitly)
- Fix CLI commands

## [1.1.2] 2018-05-07

### Fixed

- Capture the current user's username correctly when using custom User model

## [1.1.1] 2018-04-18

### Fixed

- Catch IOError when reading core-agent's manifest.json (#24)

## [1.1.0] 2018-04-13

### Added

- Reworked Django instrumentation (#19)
- Initial Flask Support (#18)
- Initial SQLAlchemy Support (#18)
- Add Request Context Support (#17)

## [1.0.3] 2018-03-26

### Fixed

- Correct the default `socket_path`

## [1.0.2] 2018-03-26

### Fixed

- Clearer archive download name

## [1.0.1] 2018-03-26

### Fixed

- Fix mismatched archive download location

## [1.0.0] 2018-03-26

Initial public release

### Added

- Django View, Template and SQL instrumentation
- Periodic CPU & Memory Readings
- Automatic management of "core agent" binary.
- Configuration settable via ENV, or Django's settings.py
