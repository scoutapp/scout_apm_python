# Changelog

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
