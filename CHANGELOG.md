# Changelog

## Pending

### Added

- Moved all decorators to the [`wrapt`
  library](https://wrapt.readthedocs.io/en/latest/) which is more transparent
  ([PR #324](https://github.com/scoutapp/scout_apm_python/pull/324)).

### Fixed

- Track SQL Alchemy `executemany` calls as multi-queries
  ([PR #340](https://github.com/scoutapp/scout_apm_python/pull/340)).
- Track Elasticsearch index name when it's not passed as a keyword argument
  ([PR #348](https://github.com/scoutapp/scout_apm_python/pull/348)).
- Increase core agent socket timeout to reduce reconnections
  ([PR #247](https://github.com/scoutapp/scout_apm_python/pull/247)).

## [2.7.0] 2019-11-03

### Added

- Python 3.8 testing and PyPI trove classifier - no code changes were required
  so older versions should work too
  ([PR #263](https://github.com/scoutapp/scout_apm_python/pull/263)).
- Capture better operation names for Django Tastypie resources, e.g.
  `myapp.api.UserResource.get_list`
  ([PR #332](https://github.com/scoutapp/scout_apm_python/pull/332)).

### Fixed

- Change `scout_apm.api.install()` signature to not take `*args, **kwargs` but
  just `config` as a keyword argument
  ([PR #304](https://github.com/scoutapp/scout_apm_python/pull/304)).
- Rewrite background samplers thread to avoid some rare race conditions
  ([PR #307](https://github.com/scoutapp/scout_apm_python/pull/307)).

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
