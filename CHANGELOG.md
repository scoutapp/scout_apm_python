# Changelog

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
